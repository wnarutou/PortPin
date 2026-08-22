# PortPin

PortPin 将本地 TCP 连接转发到目标地址，并使用指定的出站源 IP 和端口。

## 配置

编辑 `config.json`：

```json
{
  "listen_ip": "127.0.0.1",
  "listen_port": 13389,
  "source_ip": "192.168.31.31",
  "source_port": 40000,
  "remote_ip": "192.168.31.58",
  "remote_port": 3389
}
```

`source_ip` 必须是当前主机网卡上的地址，且 `source_port` 未被其他连接占用。

## 本地运行

```bash
python3 portpin.py --config config.json
```

## Docker 部署

在 `docker-compose.yml` 的 `environment` 中修改配置后执行：

```bash
docker compose up -d --build
```

查看日志：

```bash
docker compose logs -f portpin
```

Compose 使用 host 网络模式，这是为了让容器能够绑定宿主机的 `source_ip`。因此 `listen_ip` 和端口也直接作用于宿主机，配置为 `0.0.0.0` 时请同时配置防火墙规则。

Docker 部署时，Compose 环境变量会覆盖镜像内 `config.json` 中的同名配置。环境变量名为 `LISTEN_IP`、`LISTEN_PORT`、`SOURCE_IP`、`SOURCE_PORT`、`REMOTE_IP` 和 `REMOTE_PORT`。

## 发布到 Docker Hub

GitHub Actions 会在推送 `v*` 格式的 tag 时自动构建并推送镜像，例如：

```bash
git tag v1.0.0
git push origin v1.0.0
```

在 GitHub 仓库的 `Settings -> Secrets and variables -> Actions` 中添加：

- `DOCKERHUB_USERNAME`：Docker Hub 用户名
- `DOCKERHUB_TOKEN`：Docker Hub Access Token

镜像会发布为 `DOCKERHUB_USERNAME/portpin`，并生成完整版本号和 `latest` tag。
