# REC-Status

一个多录播机管理面板。

演示：https://recs.114514.plus/

## 截图

![截图_2025-03-21_14-10-24](https://github.com/user-attachments/assets/73586681-cdc9-4420-bf61-aa9926c00556)
![截图_2025-03-21_14-10-44](https://github.com/user-attachments/assets/722b1d9e-4463-4ac7-a410-6517e046881f)
![截图_2025-03-21_14-10-54](https://github.com/user-attachments/assets/f10d1a24-a2d2-492d-b397-b8bdc2acc7df)

## 部署方式

### 源码运行

需要 Python 3.10 及以上版本。

```bash
pip install -r requirements.txt
```

如果需要重新构建前端，需要 Node.js `^20.19.0 || >=22.12.0`：

```bash
cd RecStatus-web
npm ci
npm run build
```

把前端产物复制到后端静态目录：

```bash
rm -rf ../RecStatus/web/*
cp -r dist/* ../RecStatus/web/
```

从仓库根目录启动：

```bash
python RecStatus/main.py
```

也可以进入后端目录启动：

```bash
cd RecStatus
python main.py
```

默认访问地址为 `http://127.0.0.1:11111`。

### 二进制运行

从 GitHub Release 下载对应平台的压缩包，解压后直接运行其中的可执行文件。

首次启动会在可执行文件同级目录创建 `data/config.json`，并在命令行打印一次默认管理员账号和随机密码。后续启动只读取已有配置，不会再次打印密码。

二进制版日志写入可执行文件同级目录的 `logs/`。

### Docker 运行

镜像发布到 GHCR：

```bash
docker run -d \
  --name rec-status \
  -p 11111:11111 \
  -v ./data:/app/data \
  -v ./logs:/app/logs \
  ghcr.io/<owner>/<repo>:latest
```

`dev` 分支镜像会发布 `dev` 和 `latest` 标签；正式版本 tag 会发布同名镜像标签，例如 `v1.0.0`。

## 配置说明

运行配置统一使用 JSON，文件名为 `config.json`。

源码运行时默认路径为：

```text
RecStatus/data/config.json
```

二进制运行时默认路径为：

```text
可执行文件同级目录/data/config.json
```

如果没有 JSON 配置，但存在旧的 `config.yaml`，启动时会迁移到 JSON 并备份旧文件。如果 JSON 和 YAML 都不存在，程序会自动创建默认 JSON 配置。

首次自动创建配置时会随机生成 `AUTH.AUTH_KEY` 和默认用户 `admin` 的密码，密码只会在这一次启动时打印到命令行。

`HOST` 和 `PORT` 修改后需要重启服务生效；其他全局配置可以在 Web 前端的系统设置页保存后热更新。

也可以参考 `RecStatus/config.example.json` 手动创建或修改配置。

## 发布说明

- 推送到 `dev` 分支会生成 nightly 二进制预发布，并发布 GHCR `dev`、`latest` 镜像。
- 推送 `v*` tag 会创建正式 Release，并发布对应 tag 的 GHCR 镜像。
- Release Drafter 继续维护草稿发布说明。

## 计划

- 没想好

## 联系

Rec-NIC 今天也是咕咕咕的一天 108737089

（录播姬非官方闲聊群但是官方）

## 相关项目

> BililiveRecorder https://github.com/Bililive/BililiveRecorder
>
> BililiveRecorder-WebUI https://github.com/BililiveRecorder/BililiveRecorder-WebUI
>
> BLREC https://github.com/acgnhiki/blrec
