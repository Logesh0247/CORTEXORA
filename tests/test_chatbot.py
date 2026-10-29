import pandas as pd, pytest
from cortexora.analytics.metrics import enrich
from cortexora.assistant.chatbot import answer_question

@pytest.fixture
def ctx():
    orders = pd.DataFrame(dict(order_id=range(1, 61), customer_id=[(i % 10) + 1 for i in range(60)],
                               order_date=pd.date_range("2024-10-01", periods=60, freq="D").date.astype(str),
                               region=["North"] * 60, channel=["Online"] * 60))
    items = pd.DataFrame(dict(order_id=range(1, 61), product_id=[1] * 60, qty=[2] * 60,
                              unit_price=[100.] * 60, discount=[0.] * 60, unit_cost=[40.] * 60))
    df = enrich(orders, items); df["category"] = "Electronics"
    products = pd.DataFrame(dict(product_id=[1], product_name=["Electronics Product 1"], category=["Electronics"], unit_cost=[40.], list_price=[100.]))
    return dict(df=df, orders=orders, items=items, products=products,
                mkt=pd.DataFrame(dict(spend_date=["2024-01-01"], channel=["Search"], spend=[100.], clicks=[100], conversions=[10])),
                decisions=pd.DataFrame(), churn_rep=None,
                inv=pd.DataFrame(dict(product_id=[1], snapshot_date=["2024-12-01"], stock_on_hand=[1], lead_time_days=[7])))

def test_revenue_answer_uses_real_numbers(ctx):
    a = answer_question("What is our revenue and profit?", ctx)
    assert "$12,000" in a["text"] and a["table"] is not None  # 60 orders x 2 x $100

def test_definition(ctx):
    assert "seasonal-naive" in answer_question("What is WAPE?", ctx)["text"]

def test_top_category(ctx):
    a = answer_question("What is our top category?", ctx); assert "Electronics" in a["text"]

def test_navigation_hint(ctx):
    a = answer_question("Where can I run an A/B test?", ctx); assert a["navigate"] == "Experiments & Causal Lab"

def test_decisions_empty_is_honest(ctx):
    a = answer_question("What should we do next?", ctx); assert "no recommendations" in a["text"].lower()

def test_unknown_question_falls_back_helpfully(ctx):
    a = answer_question("What is the weather tomorrow?", ctx); assert "couldn't map" in a["text"]

def test_pricing_scenario_is_labelled_assumption(ctx):
    a = answer_question("What if I raise Electronics Product 1 price by 10%?", ctx)
    assert "assumption" in a["text"].lower() and "not" in a["text"].lower()
