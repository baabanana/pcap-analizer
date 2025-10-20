import streamlit as st
import tempfile
import os
from authen import check_uuid
from convertor import load_pcap, split_pcap_to_csv, split_pcap_to_json
from openai_helper import upload_files_to_vector_store, chat_with_vector_store, cleanup_files

# 从secrets或默认值获取应用配置
app_title = st.secrets.get("app", {}).get("app_title", "PCAP分析助手")
st.set_page_config(page_title=app_title, page_icon="🛡️", layout="wide")

# Cookie管理功能
@st.cache_data
def get_saved_activation_code():
    """从浏览器localStorage获取保存的激活码"""
    # 使用JavaScript获取localStorage
    return None  # 临时返回None，后面用组件实现

@st.cache_data
def get_saved_vector_store_id():
    """从浏览器localStorage获取保存的vector store ID"""
    return None  # 临时返回None，后面用组件实现

def save_activation_code(code):
    """保存激活码到session state"""
    st.session_state.activation_code = code
    st.session_state.persistent_activation_code = code

def save_vector_store_id(vector_store_id):
    """保存vector store ID到session state"""
    st.session_state.saved_vector_store_id = vector_store_id
    st.session_state.persistent_vector_store_id = vector_store_id

def get_persistent_activation_code():
    """从persistent session state获取激活码"""
    return st.session_state.get('persistent_activation_code', None)

def get_persistent_vector_store_id():
    """从persistent session state获取vector store ID"""
    return st.session_state.get('persistent_vector_store_id', None)

# 检查是否有保存的激活码和vector store
saved_code = get_persistent_activation_code()
saved_vector_store = get_persistent_vector_store_id()

if saved_code and check_uuid(saved_code):
    # 如果有有效的保存激活码
    if "session_id" not in st.session_state:
        st.session_state.session_id = saved_code

    # 如果同时有保存的vector store，直接进入chat界面
    if saved_vector_store and "step" not in st.session_state:
        st.session_state.step = "chat"
        if "vector_store_id" not in st.session_state:
            st.session_state.vector_store_id = saved_vector_store
        if "files_uploaded" not in st.session_state:
            st.session_state.files_uploaded = True
    else:
        # 只有激活码，进入upload界面
        if "step" not in st.session_state:
            st.session_state.step = "upload"
else:
    # 没有有效激活码，从认证页面开始
    if "step" not in st.session_state:
        st.session_state.step = "auth"
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
if "pcap_data" not in st.session_state:
    st.session_state.pcap_data = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "vector_store_id" not in st.session_state:
    st.session_state.vector_store_id = None
if "csv_content" not in st.session_state:
    st.session_state.csv_content = ""
if "files_uploaded" not in st.session_state:
    st.session_state.files_uploaded = False

def auth_page():
    st.title("🛡️ PCAP分析助手")
    st.markdown("### 请输入激活码")

    # 调试信息 - 显示当前保存的状态
    saved_code = get_persistent_activation_code()
    saved_vector = get_persistent_vector_store_id()
    if saved_code or saved_vector:
        with st.expander("🔍 调试信息"):
            st.write(f"保存的激活码: {saved_code[:8] + '...' if saved_code else '无'}")
            st.write(f"保存的Vector Store: {saved_vector[:8] + '...' if saved_vector else '无'}")
            st.write(f"Session State Keys: {list(st.session_state.keys())}")

    with st.form("auth_form"):
        activation_code = st.text_input("激活码", type="password", placeholder="输入20位激活码")
        submitted = st.form_submit_button("验证")

        if submitted:
            if check_uuid(activation_code):
                # 保存激活码到cookie
                save_activation_code(activation_code)
                st.session_state.session_id = activation_code
                st.session_state.step = "upload"
                st.success("激活码验证成功！")
                st.rerun()
            else:
                st.error("无效的激活码，请重试")

    st.markdown("---")
    st.markdown("### 💳 获取激活码")
    st.markdown("如需购买激活码，请点击以下链接：")
    st.markdown("🛒 [立即购买激活码](https://m.tb.cn/h.SQZU4yc?tk=ghh5f28Yp36)")
    st.markdown("🛒 [立即购买激活码](https://m.tb.cn/h.SQaDNQK?tk=W5Rnf2Rra1t)")
    st.markdown("🛒 [立即购买激活码](https://m.tb.cn/h.SQZk6iO?tk=jVh5f28g6eR)")
    st.markdown("💬 如有疑问，请联系客服获取支持")

def upload_page():
    st.title("📁 文件上传")
    st.markdown(f"**当前激活码:** `{st.session_state.session_id[:8]}...`")

    uploaded_file = st.file_uploader("选择PCAP文件", type=['pcap', 'pcapng'])

    if uploaded_file is not None:
        with st.spinner("正在处理PCAP文件..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pcap') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file_path = tmp_file.name

            try:
                packets = load_pcap(tmp_file_path)
                st.session_state.pcap_data = packets

                st.info(f"成功加载 {len(packets)} 个数据包")

                if not st.session_state.files_uploaded:
                    if st.button("🚀 处理文件并上传到AI", type="primary"):
                        with st.spinner("正在生成"):
                            csv_file = split_pcap_to_csv(packets, st.session_state.session_id)
                            json_files = split_pcap_to_json(packets, st.session_state.session_id)

                            with open(csv_file, 'r', encoding='utf-8') as f:
                                st.session_state.csv_content = f.read()

                        with st.spinner("正在上传"):
                            try:
                                vector_store_id = upload_files_to_vector_store(json_files, st.session_state.session_id)
                                if vector_store_id:
                                    st.session_state.vector_store_id = vector_store_id
                                    st.session_state.files_uploaded = True
                                    # 保存vector store ID到cookie
                                    save_vector_store_id(vector_store_id)
                                    st.success(f"✅ 文件处理完成！Vector Store ID: {vector_store_id[:8]}...")

                                    cleanup_files(json_files + [csv_file])
                                else:
                                    st.error("❌ Vector Store创建失败")
                            except Exception as e:
                                st.error(f"❌ 上传失败: {str(e)}")

                else:
                    st.success("✅ 文件已处理并上传到Vector Store")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.info(f"Vector Store: {st.session_state.vector_store_id[:8]}...")
                    with col2:
                        if st.button("🔄 重新处理文件"):
                            st.session_state.files_uploaded = False
                            st.session_state.vector_store_id = None
                            st.session_state.csv_content = ""
                            # 清除保存的vector store ID
                            vector_keys = ['saved_vector_store_id', 'persistent_vector_store_id']
                            for key in vector_keys:
                                if key in st.session_state:
                                    del st.session_state[key]
                            st.rerun()

                if st.session_state.files_uploaded:
                    if st.button("💬 进入对话分析", type="primary"):
                        st.session_state.step = "chat"
                        st.rerun()

            except Exception as e:
                st.error(f"处理文件时出错: {str(e)}")
            finally:
                os.unlink(tmp_file_path)

    # if st.button("返回激活码验证"):
    #     st.session_state.step = "auth"
    #     st.session_state.session_id = None
    #     st.session_state.files_uploaded = False
    #     st.session_state.vector_store_id = None
    #     st.session_state.csv_content = ""
    #     st.rerun()

def chat_page():
    if not st.session_state.vector_store_id:
        st.error("❌ 请先上传并处理PCAP文件")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("返回文件上传"):
                st.session_state.step = "upload"
                st.rerun()
        with col2:
            if st.button("🚪 退出登录"):
                # 清除保存的激活码和vector store ID
                keys_to_delete = [
                    'activation_code', 'saved_vector_store_id',
                    'persistent_activation_code', 'persistent_vector_store_id'
                ]
                for key in keys_to_delete:
                    if key in st.session_state:
                        del st.session_state[key]
                # 重置所有状态
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        return

    st.title("💬 PCAP分析对话")
    st.markdown(f"**激活码:** `{st.session_state.session_id[:8]}...` | **数据包数量:** {len(st.session_state.pcap_data) if st.session_state.pcap_data else 0} ")

    # 添加操作按钮和刷新提示
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("返回文件上传"):
            st.session_state.step = "upload"
            st.rerun()
    with col2:
        if st.button("🚪 退出登录"):
            # 清除保存的激活码和vector store ID
            keys_to_delete = [
                'activation_code', 'saved_vector_store_id',
                'persistent_activation_code', 'persistent_vector_store_id'
            ]
            for key in keys_to_delete:
                if key in st.session_state:
                    del st.session_state[key]
            # 重置所有状态
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    with col3:
        st.info("💡 提示: 如遇到问题，请尝试刷新页面（F5）或清除浏览器缓存")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("询问关于PCAP数据的问题..."):
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                with st.spinner("正在分析数据包..."):
                    reply = chat_with_vector_store(
                        messages=st.session_state.messages,
                        vector_store_id=st.session_state.vector_store_id,
                        csv_content=st.session_state.csv_content
                    )
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
            except Exception as e:
                st.error(f"分析失败: {str(e)}")

if st.session_state.step == "auth":
    auth_page()
elif st.session_state.step == "upload":
    upload_page()
elif st.session_state.step == "chat":
    chat_page()