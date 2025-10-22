import time
import os
from openai import OpenAI
import logging
import streamlit as st

def get_openai_client():
    """获取配置好的OpenAI客户端"""
    # 从secrets获取API密钥
    api_key = st.secrets.get("openai", {}).get("api_key")
    if api_key and api_key != "your-openai-api-key-here":
        return OpenAI(api_key=api_key)

    # 尝试从环境变量获取
    env_api_key = os.getenv("OPENAI_API_KEY")
    if env_api_key:
        return OpenAI(api_key=env_api_key)

    # 如果都没有配置，抛出错误
    raise ValueError("OpenAI API密钥未配置。请在 .streamlit/secrets.toml 中设置 openai.api_key 或设置 OPENAI_API_KEY 环境变量")

class VectorAI():
    last_response_id=None

    def __init__(self,session_id):
        self.client = get_openai_client()
        self.session_id=session_id

    def init_file(self,summary_file_path, upload_file_paths):
        self.vector_store_id=self.init_vector_store(client=self.client, 
                                               file_paths=upload_file_paths, 
                                               session_id=self.session_id)
        self.first_messages=self.system_message(summary_file_path)
        return self.vector_store_id
        
    def init_file_directly(self,summary_file_path,vector_store_id ):
        self.vector_store_id=vector_store_id
        self.first_messages=self.system_message(summary_file_path)
        return self.vector_store_id

    
    def chat(self, user_input):
        """
        使用vector store进行对话

        Args:
            messages: 对话消息列表
            vector_store_id: vector store ID
            csv_content: CSV内容作为system prompt

        Returns:
            AI回复内容
        """
        client = self.client
        vector_store_id = self.vector_store_id
        first_messages = self.first_messages

        try:
            if self.last_response_id is None:
                print("首次请求，使用初始消息")
                response = client.responses.create(
                    model="gpt-5-mini",
                    tools=[{
                            "type": "file_search",
                            "vector_store_ids": [vector_store_id]
                        }],
                    input=first_messages+[{"role": "user", "content": user_input}]
                )
                self.last_response_id = response.id
            else:
                response = client.responses.create(
                    model="gpt-5-mini",
                    tools=[{
                            "type": "file_search",
                            "vector_store_ids": [vector_store_id]
                        }],
                    previous_response_id=self.last_response_id,
                    input=[{"role": "user", "content": user_input}]
                )
                self.last_response_id = response.id
            return response.output_text

        except Exception as e:
            logging.error(f"OpenAI API调用失败: {str(e)}")
            return f"抱歉，处理您的请求时出现错误: {str(e)}"

    @staticmethod
    def init_vector_store(client, file_paths, session_id):
        """
        上传文件到OpenAI Vector Store

        Args:
            file_paths: 要上传的文件路径列表
            session_id: 会话ID，用于命名vector store

        Returns:
            vector_store_id: 创建的vector store ID
        """

        print("=" * 60)
        print("步骤1: 上传文件到 OpenAI")
        print("=" * 60)

        uploaded_file_ids = []

        for filename in file_paths:
            try:
                print(f"正在上传 {filename}...")
                with open(filename, 'rb') as f:
                    file_response = client.files.create(
                        file=f,
                        purpose='assistants'
                    )

                uploaded_file_ids.append(file_response.id)
                print(f"✓ {filename} 上传成功! File ID: {file_response.id}")

            except Exception as e:
                print(f"✗ {filename} 上传失败: {str(e)}")
                logging.error(f"文件上传失败 {filename}: {str(e)}")

        print(f"\n成功上传 {len(uploaded_file_ids)} 个文件！\n")

        print("=" * 60)
        print("步骤2: 创建 Vector Store")
        print("=" * 60)

        try:
            vector_store = client.vector_stores.create(
                name=f"PCAP Analysis - {session_id[:8]}",
                file_ids=[]
            )
            vector_store_id = vector_store.id
            print(f"✓ Vector Store 创建成功! ID: {vector_store_id}\n")

        except Exception as e:
            print(f"✗ Vector Store 创建失败: {str(e)}")
            logging.error(f"Vector Store创建失败: {str(e)}")
            return None

        print("=" * 60)
        print("步骤3: 创建 File Batch")
        print("=" * 60)

        try:
            file_batch = client.vector_stores.file_batches.create(
                vector_store_id=vector_store_id,
                file_ids=uploaded_file_ids
            )

            print(f"✓ File Batch 创建成功! ID: {file_batch.id}")
            print(f"状态: {file_batch.status}")
            print(f"文件统计: {file_batch.file_counts}\n")

            print("等待文件处理完成...")
            while file_batch.status in ['in_progress', 'cancelling']:
                time.sleep(5)
                file_batch = client.vector_stores.file_batches.retrieve(
                    vector_store_id=vector_store_id,
                    batch_id=file_batch.id
                )
                print(f"当前状态: {file_batch.status}, 文件统计: {file_batch.file_counts}")

            print(f"\n✓ Batch 处理完成! 最终状态: {file_batch.status}")

        except Exception as e:
            print(f"✗ File Batch 创建失败: {str(e)}")
            logging.error(f"File Batch创建失败: {str(e)}")
            return None

        print("\n" + "=" * 60)
        print("步骤4: 验证上传结果")
        print("=" * 60)

        try:
            vector_store_files = client.vector_stores.files.list(
                vector_store_id=vector_store_id,
                limit=100
            )

            print(f"\nVector Store 中的文件列表:")
            for idx, file in enumerate(vector_store_files.data, 1):
                status = getattr(file, 'status', 'N/A')
                print(f"{idx}. File ID: {file.id}, 状态: {status}")

            print(f"\n总计: {len(vector_store_files.data)} 个文件")

        except Exception as e:
            print(f"✗ 获取文件列表失败: {str(e)}")
            logging.error(f"获取文件列表失败: {str(e)}")

        print("\n" + "=" * 60)
        print("✓ Vector Store 创建完成！")
        print("=" * 60)
        print(f"\nVector Store ID: {vector_store_id}")

        return vector_store_id
    
    @staticmethod
    def system_message(txt_path: str):
        """初始化对话列表"""

        with open(txt_path, 'r', encoding='utf-8') as f:
            txt_content = f.read()

        system_prompt = f"""你是一个专业的网络安全专家，专门分析PCAP数据包文件。

        ## 你的任务
        1. 你需要明确网络中的可以明确的主机名称和它们的IP地址及MAC地址, 尤其是Hera, Zeus, Apollo. 并且输出给用户进行确认. 
        2. 网络中包含多个web服务器, 你需要分别明确他们的IP地址和域名，并且输出给用户进行确认.
        3. 分析网络数据包并回答用户的问题, 如果你不是100%确定, 请给用户一个数据包范围, 让他使用wireshark进行确认.
        4. 如果用户询问某个具体数据包的内容，你需要准确定位到该数据包，如果你没有查阅到相关信息, 请告诉我用户如何用wireshark查阅.
        5. 请特别注意: 网络包中包含针对三个web网页的几乎相同的访问内容, 如果用户问到http相关的内容, 请严格分辨他们. 
        6. 你可以忽略所有ipv6相关的内容

        ## 数据包摘要
        {txt_content}

        ## 回答格式要求

        ### 地址格式
        - **IP地址**：使用点分十进制格式，无空格
        - ✅ 正确：126.123.12.120
        - ❌ 错误：126. 123. 12. 120

        - **MAC地址**：使用冒号十六进制格式，无空格
        - ✅ 正确：2F:EF:86:12:21:11
        - ❌ 错误：2f ef 86 12 21 11

        ### 数值格式
        - **长度/大小**：仅输入数字，不含单位
        - ✅ 正确：220（表示220字节）
        - ❌ 错误：220 Bytes

        - **十六进制值**：
        - 不使用"0x"前缀
        - 不添加多余的前导零
        - 位数必须与数据类型匹配（如32位值用8个十六进制数字）
        - ✅ 正确：ab00cd44（32位）
        - ❌ 错误：0xab00cd44、00ab00cd44

        - **负数**：负号与数字间无空格
        - ✅ 正确：-2.13
        - ❌ 错误：- 2.13

        - **小数**：保留2位小数（四舍五入）
        - 示例：3.14159 → 3.14

        ### 其他格式
        - **邮箱地址**：不使用尖括号 < >
        - ✅ 正确：user@example.com
        - ❌ 错误：<user@example.com>

        - **URL地址**：包含完整协议
        - ✅ 正确：http://website.com
        - ❌ 错误：website.com

        - **大小写**：除非特别说明，答案不区分大小写

        ## 分析指南
        1. **准确识别初始帧/数据包**：后续问题可能依赖于正确识别初始帧，错误的帧编号将导致后续答案无效
        2. **综合利用数据源**：结合CSV摘要和vector store中的详细信息进行分析
        3. **专业性**：提供准确的网络安全分析和解释
        4. **使用中文回答**：所有回答必须使用中文

        ## 注意事项
        - 仔细检查数据包编号的准确性
        - 确保数值格式严格符合上述要求
        - 如需访问外部资源，建议在新标签页打开

        现在，请根据用户的问题提供专业分析。
        """
        system_messages = [{"role": "system", "content": system_prompt}]
        logging.info(f"完整消息: {system_messages}")
        return system_messages

def cleanup_files(file_paths):
    """清理本地文件"""
    import os
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"✓ 已删除本地文件: {file_path}")
        except Exception as e:
            print(f"✗ 删除文件失败 {file_path}: {str(e)}")

def delete_all_vector_stores(client):
    print("正在列出所有 vector store...")
    stores = client.vector_stores.list()

    if not stores.data:
        print("没有发现任何 vector store。")
        return

    for vs in stores.data:
        vs_id = vs.id
        vs_name = vs.name or "(未命名)"
        print(f"\n正在处理 Vector Store: {vs_name} ({vs_id})")

        # 先删除文件
        try:
            files = client.vector_stores.files.list(vector_store_id=vs_id)
            for f in files.data:
                print(f"  删除文件: {f.id}")
                client.vector_stores.files.delete(
                    vector_store_id=vs_id,
                    file_id=f.id
                )
        except Exception as e:
            print(f"  删除文件时出错: {e}")

        # 删除 vector store
        try:
            print(f"  删除 Vector Store: {vs_name}")
            client.vector_stores.delete(vector_store_id=vs_id)
        except Exception as e:
            print(f"  删除 Vector Store 时出错: {e}")

    print("\n✅ 所有 vector store 已删除完成。")

if __name__ == "__main__":
    ai = VectorAI(session_id="testsession_94")
    delete_all_vector_stores(ai.client)
    
    # ai.init_file_directly("data/testsession_94_summary.txt", vector_store_id="vs_68f9170a0d008191a9132e4f4437e425")
    # # ai.init_file(summary_file_path="data/testsession_94_summary.txt",
    # #          upload_file_paths=["data/testsession_94_part1.txt", "data/testsession_94_part2.txt"],)
    # print(ai.chat(user_input="请帮我分析一下这个PCAP文件中的主要通信协议有哪些？"))
    # print(ai.chat(user_input="你确定吗"))