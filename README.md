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

修改 `config.json` 后执行：

```bash
docker compose up -d --build
```

查看日志：

```bash
docker compose logs -f portpin
```

Compose 使用 host 网络模式，这是为了让容器能够绑定宿主机的 `source_ip`。因此 `listen_ip` 和端口也直接作用于宿主机，配置为 `0.0.0.0` 时请同时配置防火墙规则。
