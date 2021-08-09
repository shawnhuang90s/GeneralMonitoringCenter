FROM base_ffmpeg:1.0.5

ENV PYTHONUNBUFFERED 1
ENV application crris

COPY . .

EXPOSE 8160
EXPOSE 8161

RUN pip install -i https://pypi.douban.com/simple -r requirements.txt

# ����ͬʱ���ڶ�� CMD, ����ִֻ�����һ��
# CMD ["python", "run.py"]
# CMD ["python", "ws_alarm_data.py"]
# ����� /app ��ʾ�ڽ��� docker ���� docker exec -it crris_crris_backend_1 bash ��ĺ����ĿĿ¼
RUN chmod +x /app/start_websocket.sh
ENTRYPOINT ["/app/start_websocket.sh"]