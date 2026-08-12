from __future__ import annotations

from dataclasses import asdict

from packages.institutional import DatasetService, InstitutionalService, KnowledgeService
from packages.tools import ToolExecutionContext


def post_research_project(service: InstitutionalService, context: ToolExecutionContext, **payload) -> dict:
    return asdict(service.create_project(context, **payload))


def get_research_projects(service: InstitutionalService, context: ToolExecutionContext, repository) -> list[dict]:
    return repository.list_research_projects(context.organization_id, context.workspace_id)


def get_research_project(repository, context: ToolExecutionContext, project_id: str) -> dict | None:
    return repository.get_research_project(context.organization_id, project_id)


def post_research_run(service: InstitutionalService, context: ToolExecutionContext, **payload) -> dict:
    return asdict(service.start_run(context, **payload))


def get_research_run(repository, context: ToolExecutionContext, run_id: str) -> dict | None:
    return repository.get_research_run(context.organization_id, run_id)


def post_research_run_review(service: InstitutionalService, context: ToolExecutionContext, run_id: str, **payload) -> dict:
    return asdict(service.review(context, target_type="research_run", target_id=run_id, **payload))


def post_research_run_export(service: InstitutionalService, context: ToolExecutionContext, run_id: str) -> dict:
    return service.export_run_package(context, run_id)


def get_organization_policy(repository, context: ToolExecutionContext) -> dict | None:
    return repository.get_organization_policy(context.organization_id)


def patch_organization_policy(repository, context: ToolExecutionContext, policy) -> dict:
    if "organization.policy.update" not in context.permissions:
        raise PermissionError("organization.policy.update_required")
    return asdict(repository.upsert_organization_policy(policy))


def post_dataset(service: DatasetService, context: ToolExecutionContext, **payload) -> dict:
    return asdict(service.create_dataset(context, **payload))


def get_datasets(repository, context: ToolExecutionContext) -> list[dict]:
    rows = repository.connection.execute(
        """
        SELECT * FROM datasets
        WHERE organization_id = ? AND (workspace_id = ? OR workspace_id IS NULL) AND deleted_at IS NULL
        ORDER BY created_at DESC, id
        """,
        (context.organization_id, context.workspace_id),
    ).fetchall()
    return [dict(row) for row in rows]


def get_dataset(repository, context: ToolExecutionContext, dataset_id: str) -> dict | None:
    return repository.get_dataset(context.organization_id, dataset_id)


def post_dataset_version(service: DatasetService, context: ToolExecutionContext, dataset_id: str, **payload) -> dict:
    return asdict(service.add_version(context, dataset_id, **payload))


def post_knowledge_collection(service: KnowledgeService, context: ToolExecutionContext, **payload) -> dict:
    return asdict(service.create_collection(context, **payload))


def get_knowledge_collections(repository, context: ToolExecutionContext) -> list[dict]:
    rows = repository.connection.execute(
        """
        SELECT * FROM knowledge_collections
        WHERE organization_id = ? AND (workspace_id = ? OR workspace_id IS NULL) AND deleted_at IS NULL
        ORDER BY created_at DESC, id
        """,
        (context.organization_id, context.workspace_id),
    ).fetchall()
    return [dict(row) for row in rows]


async def post_knowledge_document(service: KnowledgeService, context: ToolExecutionContext, collection_id: str, **payload) -> dict:
    return asdict(await service.ingest_document(context, collection_id, **payload))


def post_knowledge_search(service: KnowledgeService, context: ToolExecutionContext, collection_id: str, query: str, *, project_id: str | None = None) -> list[dict]:
    return service.search(context, collection_id, query, project_id=project_id)

