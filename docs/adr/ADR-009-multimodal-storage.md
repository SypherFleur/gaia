# ADR-009: Multimodal Storage

Status: Accepted

## Context

GAIA MVP requires image upload/camera capture and must support future audio, video, document images, and BioCube media.

## Decision

Media is stored as workspace-scoped attachments with ownership metadata, modality, source, validation status, and provenance links. Images are exposed first; audio/video are schema-level future capabilities.

## Consequences

- Institution deployments can disable cloud vision providers.
- Research deployments can retain optional structured image metadata when permitted.
- Attachment isolation and safe file handling are mandatory.

