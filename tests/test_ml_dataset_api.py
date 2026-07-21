import app as application


class FakeService:
    def __init__(self):self.store=type("S",(),{"reports":None})()
    def build(self,options):return {"dataset_id":"ml-test","state":"queued","period_days":options.get("period_days",90)}
    def list(self):return [{"dataset_id":"ml-test","state":"completed","leakage_violations":0}]
    def get(self,identity):return {"progress":{"dataset_id":identity,"state":"completed"},"manifest":{"dataset_id":identity}}
    def progress(self,identity):return {"dataset_id":identity,"state":"running","processed_candles":100}
    def action(self,identity,action):return {"dataset_id":identity,"state":action+"d"}
    def validate(self,identity):return {"dataset_id":identity,"valid":True}
    def report(self,identity):return {"dataset_id":identity,"model_accuracy":None,"leakage_violations":0}


def test_ml_dataset_api_contract_is_research_only(monkeypatch):
    fake=FakeService();monkeypatch.setattr(application,"_ml_dataset_service",fake);client=application.app.test_client()
    created=client.post("/api/ml/datasets/build",json={"period_days":90}).get_json();listed=client.get("/api/ml/datasets").get_json();progress=client.get("/api/ml/datasets/ml-test/progress").get_json();validated=client.post("/api/ml/datasets/ml-test/validate").get_json();report=client.get("/api/ml/datasets/ml-test/report").get_json()
    assert created["state"]=="queued" and listed["training_enabled"] is False
    assert progress["processed_candles"]==100 and validated["valid"] is True
    assert report["model_accuracy"] is None


def test_research_ui_exposes_dataset_controls_without_predictions():
    source=open("frontend/src/pages/research-page.tsx",encoding="utf-8").read()
    for label in ("ML Dataset","Build Dataset","Pause","Resume","Cancel","Validate","Open Report"):assert label in source
    assert "prediction" not in source.lower()
