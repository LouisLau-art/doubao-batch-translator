#!/bin/bash

# Doubao Translator 服务管理脚本

SERVICE_NAME="doubao-translator"
SERVICE_FILE="/home/louis/doubao-batch-translator/doubao-translator.service"
SYSTEMD_PATH="/etc/systemd/system/"

echo "=== Doubao Translator 服务管理 ==="

case "$1" in
    install)
        echo "1. 复制服务文件到 systemd 目录..."
        sudo cp "$SERVICE_FILE" "$SYSTEMD_PATH"

        echo "2. 设置服务文件权限..."
        sudo chmod 644 "$SYSTEMD_PATH$SERVICE_NAME.service"

        echo "3. 重新加载 systemd 配置..."
        sudo systemctl daemon-reload

        echo "4. 启用服务（开机自启）..."
        sudo systemctl enable "$SERVICE_NAME"

        echo "5. 启动服务..."
        sudo systemctl start "$SERVICE_NAME"

        echo "✅ 服务安装完成！"
        ;;
    start)
        echo "启动服务..."
        sudo systemctl start "$SERVICE_NAME"
        echo "✅ 服务已启动"
        ;;
    stop)
        echo "停止服务..."
        sudo systemctl stop "$SERVICE_NAME"
        echo "✅ 服务已停止"
        ;;
    restart)
        echo "重启服务..."
        sudo systemctl restart "$SERVICE_NAME"
        echo "✅ 服务已重启"
        ;;
    status)
        echo "服务状态："
        sudo systemctl status "$SERVICE_NAME"
        ;;
    logs)
        echo "显示服务日志（按 Ctrl+C 停止）："
        sudo journalctl -u "$SERVICE_NAME" -f
        ;;
    enable)
        echo "启用开机自启..."
        sudo systemctl enable "$SERVICE_NAME"
        echo "✅ 服务已设置为开机自启"
        ;;
    disable)
        echo "禁用开机自启..."
        sudo systemctl disable "$SERVICE_NAME"
        echo "✅ 服务已禁用开机自启"
        ;;
    uninstall)
        echo "1. 停止服务..."
        sudo systemctl stop "$SERVICE_NAME" 2>/dev/null || true

        echo "2. 禁用开机自启..."
        sudo systemctl disable "$SERVICE_NAME" 2>/dev/null || true

        echo "3. 删除服务文件..."
        sudo rm -f "$SYSTEMD_PATH$SERVICE_NAME.service"

        echo "4. 重新加载 systemd 配置..."
        sudo systemctl daemon-reload

        echo "✅ 服务已卸载"
        ;;
    *)
        echo "用法: $0 {install|start|stop|restart|status|logs|enable|disable|uninstall}"
        echo ""
        echo "命令说明："
        echo "  install   - 安装并启动服务（包含开机自启）"
        echo "  start     - 启动服务"
        echo "  stop      - 停止服务"
        echo "  restart   - 重启服务"
        echo "  status    - 查看服务状态"
        echo "  logs      - 查看实时日志"
        echo "  enable    - 启用开机自启"
        echo "  disable   - 禁用开机自启"
        echo "  uninstall - 卸载服务"
        exit 1
        ;;
esac

exit 0
