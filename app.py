import streamlit as st
import tempfile
import os
import hashlib
import time
from authen import check_uuid
from convertor import load_pcap, split_pcap_to_csv, split_pcap_to_json
from openai_helper import upload_files_to_vector_store, chat_with_vector_store, cleanup_files
from streamlit_javascript import st_javascript
from streamlit_cookies_controller import CookieController

# 从secrets或默认值获取应用配置
app_title = st.secrets.get("app", {}).get("app_title", "9137网络数据包分析助手")
st.set_page_config(page_title=app_title, page_icon="🛡️", layout="wide")

# 初始化Cookie控制器
controller = CookieController(key="cookie_controller")

# Cookie管理功能
def get_saved_activation_code():
    """从浏览器Cookie获取保存的激活码"""
    try:
        cookies = controller.getAll()
        return cookies.get('activation_code', None)
    except:
        return None

def get_saved_vector_store_id():
    """从浏览器Cookie获取保存的vector store ID"""
    try:
        cookies = controller.getAll()
        return cookies.get('vector_store_id', None)
    except:
        return None

def save_activation_code(code):
    """保存激活码到Cookie和session state"""
    st.session_state.activation_code = code
    st.session_state.persistent_activation_code = code
    try:
        controller.set('activation_code', code, max_age=30*24*60*60)  # 30天过期
    except:
        pass

def save_vector_store_id(vector_store_id):
    """保存vector store ID到Cookie和session state"""
    st.session_state.saved_vector_store_id = vector_store_id
    st.session_state.persistent_vector_store_id = vector_store_id
    try:
        controller.set('vector_store_id', vector_store_id, max_age=30*24*60*60)  # 30天过期
    except:
        pass

def get_persistent_activation_code():
    """从persistent session state或Cookie获取激活码"""
    code = st.session_state.get('persistent_activation_code', None)
    if not code:
        code = get_saved_activation_code()
    return code

def get_persistent_vector_store_id():
    """从persistent session state或Cookie获取vector store ID"""
    store_id = st.session_state.get('persistent_vector_store_id', None)
    if not store_id:
        store_id = get_saved_vector_store_id()
    return store_id

# 试用功能管理
def get_device_fingerprint():
    """生成设备指纹"""
    try:
        # 获取浏览器基本信息
        fingerprint_data = st_javascript("""
            const data = {
                userAgent: navigator.userAgent,
                language: navigator.language,
                platform: navigator.platform,
                screenResolution: screen.width + 'x' + screen.height,
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                colorDepth: screen.colorDepth
            };
            JSON.stringify(data);
        """)

        if fingerprint_data:
            # 生成指纹哈希
            fingerprint_str = str(fingerprint_data)
            return hashlib.md5(fingerprint_str.encode()).hexdigest()[:16]
    except:
        pass

    # 降级方案：使用简单标识
    return "simple_fallback"

def check_trial_status():
    """检查试用状态"""
    try:
        # 从Cookie获取试用信息
        cookies = controller.getAll()
        trial_used = cookies.get('pcap_trial_used', 'false') == 'true'
        trial_date = int(cookies.get('pcap_trial_date', '0'))
        trial_count = int(cookies.get('pcap_trial_count', '0'))

        current_time = int(time.time() * 1000)  # 毫秒时间戳

        # 检查是否超过24小时（24 * 60 * 60 * 1000毫秒）
        if trial_date > 0 and current_time - trial_date > 24 * 60 * 60 * 1000:
            # 重置试用状态
            reset_trial_status()
            return {'can_trial': True, 'count': 0}

        return {
            'can_trial': not trial_used,
            'count': trial_count
        }
    except:
        pass

    return {'can_trial': True, 'count': 0}

def mark_trial_used():
    """标记试用已使用"""
    try:
        current_time = int(time.time() * 1000)
        controller.set('pcap_trial_used', 'true', max_age=24*60*60)  # 24小时过期
        controller.set('pcap_trial_date', str(current_time), max_age=24*60*60)
    except:
        pass

def increment_trial_count():
    """增加试用计数"""
    try:
        cookies = controller.getAll()
        current_count = int(cookies.get('pcap_trial_count', '0'))
        controller.set('pcap_trial_count', str(current_count + 1), max_age=24*60*60)
    except:
        pass

def reset_trial_status():
    """重置试用状态"""
    try:
        controller.remove('pcap_trial_used')
        controller.remove('pcap_trial_date')
        controller.remove('pcap_trial_count')
    except:
        pass

def is_trial_mode():
    """检查当前是否为试用模式"""
    return st.session_state.get('is_trial_mode', False)

def get_trial_limits():
    """获取试用限制配置"""
    return {
        'max_file_size': 50 * 1024 * 1024,  # 5MB
        'max_conversations': 2,  # 最多5次对话
        'max_messages_per_conversation': 2  # 每次对话最多3条消息
    }

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

    # 检查试用状态
    trial_status = check_trial_status()

    # 创建两列布局
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### 🔑 激活码登录")
        with st.form("auth_form"):
            activation_code = st.text_input("激活码", type="password", placeholder="输入20位激活码")
            submitted = st.form_submit_button("验证", type="primary")

            if submitted:
                if check_uuid(activation_code):
                    # 保存激活码到cookie
                    save_activation_code(activation_code)
                    st.session_state.session_id = activation_code
                    st.session_state.is_trial_mode = False
                    st.session_state.step = "upload"
                    st.success("激活码验证成功！")
                    st.rerun()
                else:
                    st.error("无效的激活码，请重试")

    with col2:
        st.markdown("### 🎁 免费试用")

        if trial_status['can_trial']:
            st.markdown("**试用权益：**")
            st.markdown("- 💬 对话次数：最多2次")
            st.markdown("- ⏰ 有效期：1小时")

            if st.button("🚀 开始免费试用", type="secondary"):
                # 设置试用模式
                st.session_state.is_trial_mode = True
                st.session_state.session_id = f"trial_{get_device_fingerprint()}"
                st.session_state.step = "upload"
                st.session_state.trial_count = trial_status.get('count', 0)

                # 标记试用已使用
                mark_trial_used()

                st.success("🎉 开始试用！")
                st.rerun()
        else:
            current_count = trial_status.get('count', 0)
            st.warning("⚠️ 试用已使用过")
            st.markdown(f"当前对话次数：{current_count}")
            st.markdown("24小时后可重新试用，或立即购买激活码享受完整功能")

    # 调试信息 - 显示当前保存的状态
    saved_code = get_persistent_activation_code()
    saved_vector = get_persistent_vector_store_id()
    if saved_code or saved_vector:
        with st.expander("🔍 调试信息"):
            st.write(f"保存的激活码: {saved_code[:8] + '...' if saved_code else '无'}")
            st.write(f"保存的Vector Store: {saved_vector[:8] + '...' if saved_vector else '无'}")
            st.write(f"试用状态: {trial_status}")
            st.write(f"Session State Keys: {list(st.session_state.keys())}")

    st.markdown("---")
    st.markdown("### 💳 获取激活码")
    st.markdown("如需购买激活码，请点击以下链接：")

    # 创建三列展示购买链接
    link_col1, link_col2, link_col3 = st.columns(3)
    with link_col1:
        st.markdown("🛒 [自动发货激活码](https://m.tb.cn/h.SQ0WNYk?tk=8BcAf2naspW)")
    with link_col2:
        st.markdown("🛒 [人工发货激活码](https://m.tb.cn/h.SQZU4yc?tk=ghh5f28Yp36)")
    with link_col3:
        st.markdown("🛒 [备用链接](https://m.tb.cn/h.SQaDNQK?tk=W5Rnf2Rra1t)")

def upload_page():
    st.title("📁 文件上传")

    # 显示当前状态
    if is_trial_mode():
        st.info("🎁 试用模式 - 文件大小限制50MB，对话次数限制2")
        st.markdown(f"**试用ID:** `{st.session_state.session_id[:8]}...`")
    else:
        st.markdown(f"**当前激活码:** `{st.session_state.session_id[:8]}...`")

    # 文件上传组件
    if is_trial_mode():
        uploaded_file = st.file_uploader(
            "选择PCAP文件 (试用版限制50MB)",
            type=['pcap', 'pcapng'],
            help="试用版文件大小限制为50MB，升级可享受无限制上传"
        )
    else:
        uploaded_file = st.file_uploader("选择PCAP文件", type=['pcap', 'pcapng'])

    if uploaded_file is not None:
        # 检查试用模式的文件大小限制
        if is_trial_mode():
            limits = get_trial_limits()
            file_size = len(uploaded_file.getvalue())

            if file_size > limits['max_file_size']:
                file_size_mb = file_size / (1024 * 1024)
                limit_mb = limits['max_file_size'] / (1024 * 1024)
                st.error(f"❌ 文件大小 {file_size_mb:.1f}MB 超过试用限制 {limit_mb}MB")
                st.info("💡 购买激活码可享受无文件大小限制")
                return

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

    # 试用模式升级提示
    if is_trial_mode():
        st.markdown("---")
        st.markdown("### 🚀 升级到完整版")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**🎁 试用版**")
            st.markdown("- ✅ 2次对话")
        with col2:
            st.markdown("**💎 完整版**")
            st.markdown("- 🚀 无文件大小限制")
            st.markdown("- 🚀 无对话次数限制")
        with col3:
            st.markdown("**💳 立即购买**")
            if st.button("🛒 购买激活码", type="primary", key="buy_from_upload"):
                st.session_state.step = "auth"
                st.rerun()

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
            if st.button("返回文件上传", key="return_upload_1"):
                st.session_state.step = "upload"
                st.rerun()
        with col2:
            if st.button("🚪 退出登录", key="logout_1"):
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

    # 显示当前状态
    if is_trial_mode():
        trial_count = st.session_state.get('trial_count', 0)
        limits = get_trial_limits()
        remaining = limits['max_conversations'] - trial_count

        if remaining > 0:
            st.info(f"🎁 试用模式 - 剩余对话次数: {remaining}/{limits['max_conversations']}")
        else:
            st.error("⚠️ 试用对话次数已用完，请购买激活码继续使用")

        st.markdown(f"**试用ID:** `{st.session_state.session_id[:8]}...` | **数据包数量:** {len(st.session_state.pcap_data) if st.session_state.pcap_data else 0}")
    else:
        st.markdown(f"**激活码:** `{st.session_state.session_id[:8]}...` | **数据包数量:** {len(st.session_state.pcap_data) if st.session_state.pcap_data else 0} ")

    # 添加操作按钮和刷新提示
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("返回文件上传", key="return_upload_2"):
            st.session_state.step = "upload"
            st.rerun()
    with col2:
        if st.button("🚪 退出登录", key="logout_2"):
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

    # 检查试用限制
    can_chat = True
    if is_trial_mode():
        trial_count = st.session_state.get('trial_count', 0)
        limits = get_trial_limits()

        if trial_count >= limits['max_conversations']:
            can_chat = False
            st.markdown("---")
            st.error("🚫 试用对话次数已用完")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🛒 购买激活码解锁", type="primary", key="buy_activation"):
                    st.session_state.step = "auth"
                    st.rerun()
            with col2:
                if st.button("返回文件上传", key="return_upload_3"):
                    st.session_state.step = "upload"
                    st.rerun()

    if can_chat:
        if prompt := st.chat_input("询问关于PCAP数据的问题..."):
            # 试用模式：增加对话计数
            if is_trial_mode():
                st.session_state.trial_count = st.session_state.get('trial_count', 0) + 1
                increment_trial_count()

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

                    # 试用模式：检查是否达到限制
                    if is_trial_mode():
                        trial_count = st.session_state.get('trial_count', 0)
                        limits = get_trial_limits()
                        remaining = limits['max_conversations'] - trial_count

                        if remaining <= 0:
                            st.warning("🎁 试用次数已用完！购买激活码享受无限制对话")
                        elif remaining <= 2:
                            st.info(f"💡 还剩 {remaining} 次试用机会")

                except Exception as e:
                    st.error(f"分析失败: {str(e)}")

    # 试用模式升级提示
    if is_trial_mode():
        st.markdown("---")
        st.markdown("### 🚀 升级享受完整功能")
        upgrade_col1, upgrade_col2 = st.columns(2)
        with upgrade_col1:
            st.markdown("**💎 购买激活码后：**")
            st.markdown("- 🚀 无对话次数限制")
            st.markdown("- 🚀 无文件大小限制")
        with upgrade_col2:
            if st.button("🛒 立即购买激活码", type="primary", key="chat_upgrade"):
                st.session_state.step = "auth"
                st.rerun()

if st.session_state.step == "auth":
    auth_page()
elif st.session_state.step == "upload":
    upload_page()
elif st.session_state.step == "chat":
    chat_page()