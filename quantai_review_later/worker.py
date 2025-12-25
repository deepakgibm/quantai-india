from celery_app import celery_app
import tasks.market_data
import tasks.trade_manager

if __name__ == "__main__":
    celery_app.start()
