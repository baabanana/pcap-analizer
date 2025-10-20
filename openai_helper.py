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

def upload_files_to_vector_store(file_paths, session_id):
    """
    上传文件到OpenAI Vector Store

    Args:
        file_paths: 要上传的文件路径列表
        session_id: 会话ID，用于命名vector store

    Returns:
        vector_store_id: 创建的vector store ID
    """
    client = get_openai_client()

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

def chat_with_vector_store(messages, vector_store_id, csv_content=""):
    """
    使用vector store进行对话

    Args:
        messages: 对话消息列表
        vector_store_id: vector store ID
        csv_content: CSV内容作为system prompt

    Returns:
        AI回复内容
    """
    client = get_openai_client()

    system_prompt = f"""你是一个网络安全专家，专门分析PCAP数据包。
    你有访问上传到vector store的JSON格式的详细数据包信息。

    以下是数据包的摘要信息（CSV格式）：
    {csv_content}

    请根据用户的问题，结合vector store中的详细数据包信息和上面的摘要，提供专业的网络安全分析。
    """

    full_messages = [{"role": "system", "content": system_prompt}] + messages
    logging.info(f"完整消息: {full_messages}")
    try:
        response = client.responses.parse(
            model="gpt-5-mini",
            tools=[{
                    "type": "file_search",
                    "vector_store_ids": [vector_store_id]
                }],
            input=full_messages,
        )
        logging.info(f"OpenAI响应: {response}")
        return response.output_text

    except Exception as e:
        logging.error(f"OpenAI API调用失败: {str(e)}")
        return f"抱歉，处理您的请求时出现错误: {str(e)}"

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