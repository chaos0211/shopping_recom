import click
from flask.cli import with_appcontext
from app import db
from app.models.recommend import Recommendation
from app.models.user import User
from spark_modules.recommendation_engine import RecommendationEngine
from spark_modules.data_preprocessor import DataPreprocessor

@click.group()
def recommend():
    """推荐系统相关命令"""
    pass

@recommend.command("generate")
@click.option("--user-id", type=int, help="指定用户ID")
@with_appcontext
def generate(user_id):
    """为指定用户生成推荐并写入数据库"""
    if not user_id:
        click.echo("请提供 --user-id")
        return

    preprocessor = DataPreprocessor()
    engine = RecommendationEngine(preprocessor)

    # 获取交互数据
    interactions_df = preprocessor.get_interactions_data()

    rec_df = engine.generate_recommendations(user_id=user_id, interactions_df=interactions_df)
    preprocessor.close()

    # 清除该用户已有推荐记录
    Recommendation.query.filter_by(user_id=user_id).delete()

    for row in rec_df:
        print("获取到的数据是：", row)
        db.session.add(Recommendation(
            user_id=user_id,
            product_id=int(row['product_id']),
            score=float(row['score']),
            rank=int(row['rank'])
        ))

    db.session.commit()
    click.echo(f"为用户 {user_id} 写入了 {len(rec_df)} 条推荐数据")