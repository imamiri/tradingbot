Connect to ec2

aws ec2-instance-connect ssh --instance-id i-ID

Install Requirements

pip3 install alpaca-py
pip3 install alpaca-trade-api
pip3 install lumibot --upgrade


pip install yappi # Profiling to improve performance

Steps to create a layer

mkdir python
cd python
pip install -r requirements.txt --only-binary=:all: --target .

mkdir python
zip -r lumibot_layer.zip python

aws lambda publish-layer-version --layer-name lumibot_layer \
    --zip-file fileb://lumibot_layer.zip \
    --compatible-runtimes python3.12 \
    --compatible-architectures "x86_64"



Startup script

trading_app.service

[Unit]
Description=Trading Application
After=network-online.target
Wants=network-online.target<p></p>
<p>[Service]
ExecStart=/usr/bin/python3 /home/ec2-user/tradingapp/stock_trading_bot_ma.py
Restart=always
User=ec2-user</p>


user_data.sh

#!/bin/bash
yum update -y
yum install -y python3
pip3 install -r /home/ec2-user/tradingapp/requirements.txt<p></p>
<h1>Copy the systemd service file to the correct location</h1>
<p>cp /home/ec2-user/tradingapp/trading_app.service /etc/systemd/system/</p>
<h1>Enable and start the systemd service</h1>

 
Set userdata in ec2 isntance config

