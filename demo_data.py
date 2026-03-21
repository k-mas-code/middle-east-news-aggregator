"""
Demo data generator for local testing.

Creates sample reports that can be viewed in the UI without Firestore.
"""

from datetime import datetime, timedelta
from middle_east_aggregator.models import (
    Article, Cluster, Report, ComparisonResult,
    SentimentResult, Entity
)

def generate_demo_reports():
    """Generate demo reports for UI testing."""

    # Demo Report 1: Gaza Conflict
    articles_gaza = [
        Article(
            id="art-1",
            url="https://www.aljazeera.com/news/2024/01/gaza-humanitarian-crisis",
            title="ガザの人道危機が深刻化",
            content="ガザの人道状況は悪化を続けており、援助団体は民間人への必要不可欠なサービスの提供に苦慮している。国際監視団は、継続する封鎖と、それが医薬品や食料配給に与える影響について懸念を表明した。援助物資の不足により、多くの家族が基本的な生活必需品へのアクセスに困難を抱えている状況だ。",
            published_at=datetime(2024, 1, 15, 10, 0),
            media_name="aljazeera",
            is_middle_east=True,
            collected_at=datetime(2024, 1, 15, 11, 0)
        ),
        Article(
            id="art-2",
            url="https://www.reuters.com/world/middle-east/gaza-aid-2024",
            title="ガザへの国際援助活動",
            content="民間人への懸念が高まる中、複数の国がガザへの追加人道支援を表明した。国連は、重要な医薬品と食料支援を届けるための即時アクセスを求めている。国際社会からの支援の呼びかけが強まっており、緊急の人道的対応が必要とされている。",
            published_at=datetime(2024, 1, 15, 9, 30),
            media_name="reuters",
            is_middle_east=True,
            collected_at=datetime(2024, 1, 15, 11, 0)
        ),
        Article(
            id="art-3",
            url="https://www.bbc.com/news/world-middle-east-gaza-update",
            title="ガザ：援助機関が深刻な物資不足を報告",
            content="ガザで活動する援助機関は、医薬品と必要物資の深刻な不足を報告している。状況はますます切迫しており、多くの家族が基本的な生活必需品へのアクセスに苦労している。医療施設も物資不足に直面し、適切な治療の提供が困難な状態が続いている。",
            published_at=datetime(2024, 1, 15, 8, 0),
            media_name="bbc",
            is_middle_east=True,
            collected_at=datetime(2024, 1, 15, 11, 0)
        )
    ]

    cluster_gaza = Cluster(
        id="cluster-1",
        topic_name="ガザ人道危機",
        articles=articles_gaza,
        media_names=["aljazeera", "reuters", "bbc"],
        created_at=datetime(2024, 1, 15, 11, 0)
    )

    comparison_gaza = ComparisonResult(
        media_bias_scores={
            "aljazeera": SentimentResult(polarity=-0.4, subjectivity=0.6, label="negative"),
            "reuters": SentimentResult(polarity=-0.2, subjectivity=0.4, label="negative"),
            "bbc": SentimentResult(polarity=-0.3, subjectivity=0.5, label="negative")
        },
        unique_entities_by_media={
            "aljazeera": [Entity(text="blockade", label="EVENT", count=2)],
            "reuters": [Entity(text="UN", label="ORG", count=3)],
            "bbc": [Entity(text="aid agencies", label="ORG", count=2)]
        },
        common_entities=[
            Entity(text="Gaza", label="GPE", count=15),
            Entity(text="humanitarian aid", label="EVENT", count=8)
        ],
        bias_diff=0.2
    )

    report_gaza = Report(
        id="report-1",
        cluster=cluster_gaza,
        comparison=comparison_gaza,
        generated_at=datetime(2024, 1, 15, 11, 30),
        summary="3つの全メディアがガザの悪化する人道状況を報道。Al Jazeeraは封鎖の影響を強調し、Reutersは国際援助活動に焦点を当て、BBCは援助機関の報告をハイライトしている。感情分析では全ソースで一貫してネガティブな報道が見られ、Al Jazeeraが最も強いネガティブ極性(-0.4)を示している。"
    )

    # Demo Report 2: Syria Peace Talks
    articles_syria = [
        Article(
            id="art-4",
            url="https://www.aljazeera.com/news/2024/01/syria-peace-talks",
            title="シリア和平交渉がジュネーブで再開",
            content="シリア紛争解決に向けた外交努力がジュネーブで再開され、複数国の代表が参加している。交渉は、戦争で荒廃した国における恒久的な平和と復興のための枠組み確立を目指している。主要な利害関係者が停戦協定と人道回廊について議論を行っている。",
            published_at=datetime(2024, 1, 14, 14, 0),
            media_name="aljazeera",
            is_middle_east=True,
            collected_at=datetime(2024, 1, 14, 15, 0)
        ),
        Article(
            id="art-5",
            url="https://www.reuters.com/world/middle-east/syria-geneva-talks",
            title="ジュネーブ：シリア交渉が2日目に突入",
            content="シリアの和平交渉がジュネーブで2日目に入り、国際調停者から慎重な楽観論が示されている。主要な関係者は停戦協定と人道回廊について議論している。長期的な平和への道筋を探る重要な協議が続けられており、国際社会からの注目が集まっている。",
            published_at=datetime(2024, 1, 14, 13, 30),
            media_name="reuters",
            is_middle_east=True,
            collected_at=datetime(2024, 1, 14, 15, 0)
        )
    ]

    cluster_syria = Cluster(
        id="cluster-2",
        topic_name="シリア和平交渉",
        articles=articles_syria,
        media_names=["aljazeera", "reuters"],
        created_at=datetime(2024, 1, 14, 15, 0)
    )

    comparison_syria = ComparisonResult(
        media_bias_scores={
            "aljazeera": SentimentResult(polarity=0.1, subjectivity=0.5, label="neutral"),
            "reuters": SentimentResult(polarity=0.2, subjectivity=0.4, label="positive")
        },
        unique_entities_by_media={
            "aljazeera": [Entity(text="reconstruction", label="EVENT", count=1)],
            "reuters": [Entity(text="mediators", label="PERSON", count=2)]
        },
        common_entities=[
            Entity(text="Syria", label="GPE", count=10),
            Entity(text="Geneva", label="GPE", count=6)
        ],
        bias_diff=0.1
    )

    report_syria = Report(
        id="report-2",
        cluster=cluster_syria,
        comparison=comparison_syria,
        generated_at=datetime(2024, 1, 14, 15, 30),
        summary="シリア和平交渉の報道はわずかな楽観を示しており、Reutersがより肯定的な感情(0.2)を示すのに対し、Al Jazeeraは中立的な立場(0.1)を取っている。両メディアは異なる側面を強調：Al Jazeeraは復興目標に焦点を当て、Reutersは国際調停者の役割をハイライトしている。"
    )

    # Demo Report 3: Israel-Lebanon Border
    article_lebanon = Article(
        id="art-6",
        url="https://www.bbc.com/news/world-middle-east-israel-lebanon",
        title="イスラエル・レバノン国境で緊張が高まる",
        content="最近の砲火の応酬を受けて、イスラエル・レバノン国境沿いで軍事活動が増加している。国連平和維持軍は、事態のエスカレーションを防ぐため、双方に自制を呼びかけている。地域の安定性への懸念が高まっており、国際社会が状況を注視している。",
        published_at=datetime(2024, 1, 13, 16, 0),
        media_name="bbc",
        is_middle_east=True,
        collected_at=datetime(2024, 1, 13, 17, 0)
    )

    cluster_lebanon = Cluster(
        id="cluster-3",
        topic_name="イスラエル・レバノン国境緊張",
        articles=[article_lebanon],
        media_names=["bbc"],
        created_at=datetime(2024, 1, 13, 17, 0)
    )

    comparison_lebanon = ComparisonResult(
        media_bias_scores={
            "bbc": SentimentResult(polarity=-0.1, subjectivity=0.4, label="neutral")
        },
        unique_entities_by_media={
            "bbc": [
                Entity(text="UN peacekeepers", label="ORG", count=1),
                Entity(text="Israel", label="GPE", count=3),
                Entity(text="Lebanon", label="GPE", count=3)
            ]
        },
        common_entities=[
            Entity(text="Israel-Lebanon border", label="LOC", count=2)
        ],
        bias_diff=0.0
    )

    report_lebanon = Report(
        id="report-3",
        cluster=cluster_lebanon,
        comparison=comparison_lebanon,
        generated_at=datetime(2024, 1, 13, 17, 30),
        summary="BBCがイスラエル・レバノン国境での緊張の高まりを中立的な感情で報道。報道は国連平和維持軍の自制呼びかけを強調している。BBCのみがこのトピックを取り上げたため、比較分析は利用できない。"
    )

    return [report_gaza, report_syria, report_lebanon]


if __name__ == "__main__":
    reports = generate_demo_reports()
    print(f"Generated {len(reports)} demo reports:")
    for report in reports:
        print(f"  - {report.cluster.topic_name} ({len(report.cluster.articles)} articles)")
