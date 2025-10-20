import streamlit as st
import tempfile
import os
from openai import OpenAI
from authen import check_uuid
from convertor import load_pcap, split_pcap_to_csv, split_pcap_to_json
from openai_helper import upload_files_to_vector_store, chat_with_vector_store, cleanup_files

st.set_page_config(page_title="PCAP分析助手", page_icon="🛡️", layout="wide")

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

    with st.form("auth_form"):
        activation_code = st.text_input("激活码", type="password", placeholder="输入20位激活码")
        submitted = st.form_submit_button("验证")

        if submitted:
            if check_uuid(activation_code):
                st.session_state.session_id = activation_code
                st.session_state.step = "upload"
                st.success("激活码验证成功！")
                st.rerun()
            else:
                st.error("无效的激活码，请重试")

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
        if st.button("返回文件上传"):
            st.session_state.step = "upload"
            st.rerun()
        return

    st.title("💬 PCAP分析对话")
    st.markdown(f"**激活码:** `{st.session_state.session_id[:8]}...` | **数据包数量:** {len(st.session_state.pcap_data) if st.session_state.pcap_data else 0} | **Vector Store:** `{st.session_state.vector_store_id[:8]}...`")

    if st.button("返回文件上传"):
        st.session_state.step = "upload"
        st.rerun()

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