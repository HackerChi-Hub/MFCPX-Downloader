# 百度网盘批量转存工具

## 📖 项目说明

本工具用于批量转存百度网盘分享链接到指定目录，无需打开浏览器，直接调用百度网盘API。

## ✅ 成功方法：baidu_transfer_api.py

**原理**：从已登录的 Chrome Profile 7 提取真实Cookie，直接调用百度网盘HTTP转存API。

### 使用方法

```bash
# 正常运行（转存到 /mac/FCP插件）
python3 baidu_transfer_api.py --dest "/mac/FCP插件"

# 测试模式（只处理第一条）
python3 baidu_transfer_api.py --test

# 指定间隔时间（默认4秒）
python3 baidu_transfer_api.py --delay 5

# 查看帮助
python3 baidu_transfer_api.py --help
```

### 依赖安装

```bash
pip install requests browser-cookie3 --break-system-packages
```

### 文件说明

- `baidu_share_links.txt` - 分享链接列表（格式：链接 密码）
- `transfer_api_progress.json` - 进度记录（支持断点续传）

## 📊 实际使用结果

**2025-05-06 转存记录**：
- 总链接数：85个
- 成功转存：69个
- 失败：12个
- 成功率：81.2%

**失败原因分析**：
- 提取码错误/已失效：8个
- 分享已失效（无文件）：2个
- 其他问题：2个

**目标目录**：`/mac/FCP插件/`

## 🗑️ 已废弃的方法

以下方法已被 `baidu_transfer_api.py` 取代，已删除：

- `baidu_auto_save.user.js` - 油猴脚本（需要打开浏览器）
- `baidu_batch_downloader.py` - 浏览器自动化版本
- `baidu_downloader.py` - 早期版本
- `baidu_share_saver.py` - 需要浏览器界面

**废弃原因**：
1. 需要打开浏览器界面，不稳定
2. 无法批量自动化处理
3. 容易被反爬虫机制拦截
4. 资源占用大

## ⚠️ 注意事项

1. **Chrome Profile**：需要确保 Chrome Profile 7 中已登录百度网盘
2. **目标目录**：确保目标目录存在于百度网盘中
3. **频率限制**：默认每条链接间隔4秒，避免触发频率限制
4. **Cookie有效期**：如果提示登录过期，需要重新登录百度网盘

## 📝 链接格式

支持两种格式：

```
https://pan.baidu.com/s/1xxxxx  提取码
https://pan.baidu.com/s/1xxxxx?pwd=提取码
```

## 🔍 故障排除

**登录过期**：
```
❌ 未登录或 Cookie 已过期
```
解决：打开 Chrome，登录百度网盘，然后重新运行

**目录不存在**：
```
❌ errno=2 | 转存路径不存在
```
解决：在百度网盘中手动创建目标目录

**频率限制**：
```
❌ errno=130 | 触发频率限制
```
解决：增加 `--delay` 参数的值（如 `--delay 10`）

## 📞 反馈

如有问题，请检查 `transfer_api_progress.json` 中的错误信息。

---

**最后更新**：2025-05-06  
**成功率**：81.2% (69/85)  
**维护者**：HackerChi-Hub
