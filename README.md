# Human Resource Bot
This is a Discord bot created for a virtual game show "Human Resources" (HR). Its intention is to create additional functionality for administering Discord and to monitor direct messages between users. This bot is not particularly dynamic as almost all functionality doesn't make sense outside the context of HR.

## To restart the bot:
sudo systemctl restart bot.service

## To find the services:
/lib/systemd/system/bot.service

## To view the tail of the logs:
journalctl -t python -f

## The bot.service file:

```[Unit]
Description=Bot Service
After=multi-user.target

[Service]
Type=simple
Restart=always
ExecStart=/root/HRbot/venv/bin/python /root/HRbot/bot.py | /usr/bin/systemd-cat -ttrue-service
StandardOutput=journal+console
EnvironmentFile=/root/HRbot/active.env


[Install]
WantedBy=multi-user.target```
