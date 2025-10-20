# PCAP分析助手

一个基于AI的网络安全分析工具，专门用于分析PCAP格式的网络数据包文件。

## 功能特性

- 🔐 激活码验证系统
- 📁 PCAP/PCAPNG文件处理
- 🤖 AI驱动的智能分析
- 💬 交互式对话分析
- 🍪 智能状态保存

## 环境配置

### 1. 安装依赖

```bash
pip install streamlit openai scapy
```

### 2. 配置Secrets

复制并编辑secrets配置文件：

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

在 `.streamlit/secrets.toml` 中填入你的OpenAI API密钥：

```toml
[openai]
api_key = "sk-your-actual-openai-api-key"
```

### 3. 环境变量（可选）

如果不使用secrets文件，也可以设置环境变量：

```bash
export OPENAI_API_KEY="sk-your-actual-openai-api-key"
```

## 运行应用

```bash
streamlit run app.py
```

## 使用说明

1. 输入有效的激活码
2. 上传PCAP文件
3. 等待文件处理和AI分析
4. 开始对话式分析

## 激活码管理

激活码列表在 `authen.py` 文件中维护。当前包含测试激活码 `root_not_delete`。

## 部署注意事项

- 确保 `.streamlit/secrets.toml` 文件已被 `.gitignore` 忽略
- 在生产环境中使用真实的OpenAI API密钥
- 根据需要调整文件上传大小限制

## 安全说明

- 激活码和API密钥不会被提交到版本控制
- 所有敏感信息都应通过secrets或环境变量配置
- 建议定期轮换API密钥