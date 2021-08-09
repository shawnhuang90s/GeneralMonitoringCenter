FROM base_ffmpeg:1.0.5

ENV PYTHONUNBUFFERED 1
ENV application crris

COPY . .

EXPOSE 8160
EXPOSE 8161

RUN pip install -i https://pypi.douban.com/simple -r requirements.txt

# 不能同时存在多个 CMD, 否则只执行最后一个
# CMD ["python", "run.py"]
# CMD ["python", "ws_alarm_data.py"]
# 这里的 /app 表示在进入 docker 容器 docker exec -it crris_crris_backend_1 bash 后的后端项目目录
RUN chmod +x /app/start_websocket.sh
ENTRYPOINT ["/app/start_websocket.sh"]