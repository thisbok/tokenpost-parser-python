"""Bedrock Knowledge Base Sync - Knowledge Base 데이터 소스 동기화를 수행합니다."""

import time
import boto3
from botocore.exceptions import ClientError
from typing import Optional, Dict
from config import AWS_REGION, KNOWLEDGE_BASE_ID, DATA_SOURCE_ID


class BedrockKnowledgeBaseSync:
    def __init__(
        self,
        knowledge_base_id: str = KNOWLEDGE_BASE_ID,
        data_source_id: str = DATA_SOURCE_ID,
        region: str = AWS_REGION,
    ):
        self.knowledge_base_id = knowledge_base_id
        self.data_source_id = data_source_id
        self.client = boto3.client("bedrock-agent", region_name=region)

    def start_ingestion_job(self) -> Optional[Dict]:
        """Knowledge Base 데이터 소스 동기화(ingestion) 작업을 시작합니다."""
        if not self.knowledge_base_id or not self.data_source_id:
            print("Error: KNOWLEDGE_BASE_ID와 DATA_SOURCE_ID가 설정되어야 합니다.")
            return None

        try:
            response = self.client.start_ingestion_job(
                knowledgeBaseId=self.knowledge_base_id,
                dataSourceId=self.data_source_id,
            )

            job_info = response.get("ingestionJob", {})
            print(f"Ingestion job started:")
            print(f"  Job ID: {job_info.get('ingestionJobId')}")
            print(f"  Status: {job_info.get('status')}")

            return job_info
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "ConflictException":
                print("Warning: 이미 진행 중인 ingestion job이 있습니다.")
            else:
                print(f"Error starting ingestion job: {e}")
            return None

    def get_ingestion_job_status(self, job_id: str) -> Optional[Dict]:
        """Ingestion job의 상태를 확인합니다."""
        try:
            response = self.client.get_ingestion_job(
                knowledgeBaseId=self.knowledge_base_id,
                dataSourceId=self.data_source_id,
                ingestionJobId=job_id,
            )
            return response.get("ingestionJob", {})
        except ClientError as e:
            print(f"Error getting job status: {e}")
            return None

    def wait_for_completion(self, job_id: str, timeout: int = 600, poll_interval: int = 10) -> bool:
        """Ingestion job이 완료될 때까지 대기합니다."""
        start_time = time.time()
        completed_statuses = ["COMPLETE", "FAILED", "STOPPED"]

        print(f"Waiting for ingestion job {job_id} to complete...")

        while time.time() - start_time < timeout:
            job_info = self.get_ingestion_job_status(job_id)
            if not job_info:
                return False

            status = job_info.get("status", "")
            print(f"  Status: {status}")

            if status in completed_statuses:
                if status == "COMPLETE":
                    statistics = job_info.get("statistics", {})
                    print(f"\nIngestion completed successfully!")
                    print(f"  Documents scanned: {statistics.get('numberOfDocumentsScanned', 0)}")
                    print(f"  Documents indexed: {statistics.get('numberOfNewDocumentsIndexed', 0)}")
                    print(f"  Documents modified: {statistics.get('numberOfModifiedDocumentsIndexed', 0)}")
                    print(f"  Documents deleted: {statistics.get('numberOfDocumentsDeleted', 0)}")
                    print(f"  Documents failed: {statistics.get('numberOfDocumentsFailed', 0)}")
                    return True
                else:
                    failure_reasons = job_info.get("failureReasons", [])
                    print(f"\nIngestion job {status}")
                    if failure_reasons:
                        print(f"  Failure reasons: {failure_reasons}")
                    return False

            time.sleep(poll_interval)

        print(f"Timeout waiting for ingestion job to complete")
        return False

    def sync_and_wait(self, timeout: int = 600) -> bool:
        """동기화를 시작하고 완료될 때까지 대기합니다."""
        job_info = self.start_ingestion_job()
        if not job_info:
            return False

        job_id = job_info.get("ingestionJobId")
        if not job_id:
            print("Error: Job ID not found")
            return False

        return self.wait_for_completion(job_id, timeout)

    def list_ingestion_jobs(self, max_results: int = 10) -> list:
        """최근 ingestion job 목록을 반환합니다."""
        try:
            response = self.client.list_ingestion_jobs(
                knowledgeBaseId=self.knowledge_base_id,
                dataSourceId=self.data_source_id,
                maxResults=max_results,
                sortBy={"attribute": "STARTED_AT", "order": "DESCENDING"},
            )
            return response.get("ingestionJobSummaries", [])
        except ClientError as e:
            print(f"Error listing ingestion jobs: {e}")
            return []


if __name__ == "__main__":
    sync = BedrockKnowledgeBaseSync()

    # 최근 작업 확인
    print("Recent ingestion jobs:")
    jobs = sync.list_ingestion_jobs(max_results=5)
    for job in jobs:
        print(f"  - {job.get('ingestionJobId')}: {job.get('status')} ({job.get('startedAt')})")

    # 새 동기화 시작
    print("\nStarting new sync...")
    success = sync.sync_and_wait(timeout=300)
    print(f"\nSync {'successful' if success else 'failed'}")
