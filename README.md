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
  "remote_port": 3389,
  "reset_on_disconnect": true
}
```

`source_ip` 必须是当前主机网卡上的地址，且 `source_port` 未被其他连接占用。

## 断开后快速重连

固定源 IP、源端口和目标地址意味着每次连接使用相同的 TCP 四元组。普通关闭可能使旧连接进入 `TIME_WAIT`，导致立即重连时出现 `Address already in use`（Linux errno 98 / Windows 10048）；仅设置 `SO_REUSEADDR` 无法保证立即重连。

`reset_on_disconnect` 默认为 `true`：隧道结束时使用 TCP RST 关闭出站连接，避免本端正常关闭产生的 `TIME_WAIT` 占用固定源端口，适用于断开后需要立即重连的远程桌面。此方式会丢弃旧连接中尚未发送完的数据。如果用途要求正常 TCP 关闭，可将其设为 `false`，但可能需要等待旧连接状态过期后才能重连。本程序仍会在任一端关闭时结束整个隧道，不提供完整的 TCP 半关闭支持。

同一组固定源地址与目标地址只能有一个活动 TCP 连接。当前程序串行处理连接；手机锁屏、断网或切换网络后，如果旧连接未发出 FIN/RST，程序可能仍在等待旧连接，新连接也会等待。上述快速关闭配置只解决已检测到断开的端口释放问题，不会主动踢掉仍然活动的连接。

排查时查看日志：如果已出现 `Connection closed`，接着出现地址占用错误，检查是否已更新程序以及是否启用了快速关闭；如果始终没有 `Peer closed connection` 或 `Connection closed`，则需要进一步排查旧连接未被检测为断开的情况。更新前遗留的 TCP 状态可能仍需等待一次过期。

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

Docker 部署时，Compose 环境变量会覆盖镜像内 `config.json` 中的同名配置。环境变量名为 `LISTEN_IP`、`LISTEN_PORT`、`SOURCE_IP`、`SOURCE_PORT`、`REMOTE_IP`、`REMOTE_PORT` 和 `RESET_ON_DISCONNECT`（`true` / `false`）。

## 测试

```bash
python3 -m unittest -v
```

测试使用本机 TCP 连接验证双向转发、固定源端口连续重连、正常关闭选项和配置校验，不需要连接实际远程桌面。

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
