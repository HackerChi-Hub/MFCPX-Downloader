# MFCPX-Downloader

> FCP插件批量下载工具 - 支持百度网盘、阿里云盘等网盘资源的自动化批量保存

## 📖 项目简介

本项目用于从 [MFCPX论坛](https://fcpfx.com/) 批量下载 FCP 插件资源，支持多种网盘平台的自动化批量保存。

### ✨ 主要功能

- 🔍 **自动爬取**：从论坛爬取分享链接
- 🔄 **批量转存**：支持百度网盘、阿里云盘等
- 📊 **进度记录**：支持断点续传
- 🚀 **无浏览器**：直接调用API，无需打开浏览器

## 🚀 快速开始

### 1. 百度网盘批量转存（推荐）

**成功方法**：使用 `baidu_transfer_api.py` - 直接调用百度网盘API

```bash
# 安装依赖
pip install requests browser-cookie3 --break-system-packages

# 使用方法
python3 baidu_transfer_api.py --dest "/mac/FCP插件" --delay 4

# 测试模式（只处理第一条）
python3 baidu_transfer_api.py --test
```

**特点**：
- ✅ 从 Chrome 自动提取 Cookie
- ✅ 无需打开浏览器
- ✅ 支持断点续传
- ✅ 成功率：81.2% (69/85)

详细文档：[BAIDU_TRANSFER_README.md](BAIDU_TRANSFER_README.md)

### 2. 阿里云盘下载

```bash
python3 alist_downloader.py
```

### 3. 完整流程（爬取+下载）

```bash
# 爬取论坛链接
python3 mfcpx_pipeline.py

# 批量转存
python3 baidu_transfer_api.py --dest "/mac/FCP插件"
```

## 📁 项目结构

```
MFCPX-Downloader/
├── baidu_transfer_api.py          # ✅ 百度网盘API转存（推荐）
├── alist_downloader.py            # 阿里云盘下载器
├── mfcpx_pipeline.py              # 完整爬取流程
├── baidu_share_links.txt          # 百度网盘链接列表
├── transfer_api_progress.json     # 转存进度记录
├── BAIDU_TRANSFER_README.md       # 百度转存详细文档
└── README.md                      # 本文件
```

## 📊 使用统计

**百度网盘批量转存（2025-05-06）**：
- 总链接数：85个
- 成功转存：69个  
- 失败：12个
- 成功率：81.2%

## ⚠️ 注意事项

1. **Chrome Profile**：需要 Chrome Profile 7 中已登录百度网盘
2. **目标目录**：确保 `/mac/FCP插件` 目录存在于百度网盘中
3. **频率限制**：默认间隔4秒，避免触发限制
4. **Cookie有效**：如提示登录过期，需重新登录百度网盘

## 🔧 故障排除

### 常见问题

**登录过期**：
```
❌ 未登录或 Cookie 已过期
```
解决：打开 Chrome，登录百度网盘，重新运行

**目录不存在**：
```
❌ errno=2 | 转存路径不存在
```
解决：在百度网盘中手动创建目标目录

**频率限制**：
```
❌ errno=130 | 触发频率限制
```
解决：增加 `--delay` 参数值（如 `--delay 10`）

## 🗑️ 已废弃的方法

以下方法已被 `baidu_transfer_api.py` 取代：

- ❌ `baidu_auto_save.user.js` - 需要浏览器界面
- ❌ `baidu_batch_downloader.py` - 浏览器自动化不稳定
- ❌ `baidu_downloader.py` - 早期版本
- ❌ `baidu_share_saver.py` - 需要手动操作

**废弃原因**：
1. 需要打开浏览器界面，不稳定
2. 无法批量自动化处理
3. 容易被反爬虫机制拦截
4. 资源占用大

## 📝 更新日志

### 2025-05-06
- ✅ 新增百度网盘API直接转存功能
- ✅ 清理废弃的浏览器自动化方法
- ✅ 添加详细文档和故障排除指南
- ✅ 成功率提升至 81.2%

## 📞 反馈与支持

如有问题，请查看：
- [百度转存详细文档](BAIDU_TRANSFER_README.md)
- [完全自动化使用指南](完全自动化使用指南.md)
- [阿里云盘客户端使用指南](阿里云盘客户端使用指南.md)

## 📄 许可证

MIT License

---

**最后更新**：2025-05-06  
**维护者**：HackerChi-Hub  
**仓库地址**：https://github.com/HackerChi-Hub/MFCPX-Downloader
