from airflow import DAG
from pendulum.tz.timezone import Timezone
from pendulum.duration import Duration
from pendulum.datetime import DateTime
from airflow.operators.empty import EmptyOperator
from datetime import timedelta
from airflow.models import Variable
from airflow.providers.google.cloud.operators.dataform import (
    DataformCreateCompilationResultOperator,
    DataformCreateWorkflowInvocationOperator,
)


# DAG CONSTANT VALUES
__version__ = "1.0.0"
DAG_NAME = "Deploy_dataform_init"
DAG_ID = f"{DAG_NAME}_{__version__}"
TIMEZONE = Timezone("Europe/Warsaw")
START_DATE = DateTime(2023, 5, 5, 10, 0, 0, 0, TIMEZONE)
SCHEDULE = None

# FLOW CONFIGURATION CONSTANT VALUES
ENV = Variable.get("env")
if ENV == "dev":
    LOCATION = "europe-west3"
    PROJECT_ID = "data-prep-test-rafal"
    REPOSITORY_ID = "DataMigration"
    BRANCH_NAME = "migracja_danych"

elif ENV == "test":
    LOCATION = "europe-west3"
    PROJECT_ID = "dss-cdw-test-0"
    REPOSITORY_ID = "dss-gcp-dataform"
    BRANCH_NAME = "test"
elif ENV == "prod":
    LOCATION = "europe-west3"
    PROJECT_ID = "dss-cdw-prod-0"
    REPOSITORY_ID = "dss-gcp-dataform"
    BRANCH_NAME = "prod"
else:
    raise ValueError()
# CONN_ID'S
GOOGLE_CONN_ID = "dss_google_cloud"

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": START_DATE,
    "email": None,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "tags": ["poc", "dss"],
    "retry_delay": timedelta(minutes=1),
}

compilation_result = {
    "git_commitish": BRANCH_NAME,
    "code_compilation_config": {"default_database": PROJECT_ID},
}

with DAG(
    dag_id=DAG_ID,
    schedule=SCHEDULE,
    start_date=START_DATE,
    catchup=False,
    dagrun_timeout=Duration(minutes=60),
    default_args=default_args,
    render_template_as_native_obj=True,
    params=None,
) as dag:
    start = EmptyOperator(task_id="Start_task")

    create_dataform_compilation_result = DataformCreateCompilationResultOperator(
        task_id="create_dataform_compilation_result",
        project_id=PROJECT_ID,
        region=LOCATION,
        repository_id=REPOSITORY_ID,
        compilation_result=compilation_result,
        gcp_conn_id=GOOGLE_CONN_ID,
    )

    create_dataform_workflow_invocation = DataformCreateWorkflowInvocationOperator(
        task_id="create_dataform_workflow_invocation",
        project_id=PROJECT_ID,
        region=LOCATION,
        repository_id=REPOSITORY_ID,
        workflow_invocation={
            "compilation_result": "{{ task_instance.xcom_pull('create_dataform_compilation_result')['name'] }}",
            "invocation_config": {"included_tags": ["init"]},
        },
        gcp_conn_id=GOOGLE_CONN_ID,
    )

    end = EmptyOperator(task_id="End_task")

    (
        start
        >> create_dataform_compilation_result
        >> create_dataform_workflow_invocation
        >> end
    )
    