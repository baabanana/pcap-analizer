# 生成20位的UUID, 一共50个, 搞个表
import uuid
import streamlit as st
import os
# 从os中读取环境变量
ENV_UUIDS = os.getenv("ACTIVATION_CODES", "")
DEFAULT_UUIDS=[]
if ENV_UUIDS:
    DEFAULT_UUIDS = ENV_UUIDS.split(',')

def generate_uuids(n=50):
    uuids = [str(uuid.uuid4()).replace('-', '')[:20] for _ in range(n)]
    return uuids

# 默认激活码列表

def check_uuid(uuid_to_check):
    # 从secrets读取激活码列表
    secret_uuids = st.secrets.get("auth", {}).get("activation_codes", [])
    if secret_uuids:
        return uuid_to_check in secret_uuids
    else:
        return uuid_to_check in DEFAULT_UUIDS

if __name__ == "__main__":
    uuid_list = DEFAULT_UUIDS
    for u in uuid_list:
        print(f"{u}")
    print(uuid_list)

