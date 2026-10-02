# Repository ownership theo role

Theo yêu cầu người dùng, mỗi role có một folder chứa logic và docs riêng. Cấu trúc hiện có đã tách runtime; lần này hoàn thiện ownership/navigation và chuyển docs đúng role.

```text
P-076/
├── backend/                domain, models, DB/migrations, worker, VLM
│   ├── AGENTS.md
│   ├── README.md
│   └── docs/               implementation, architecture, development, runbook, work-items
├── api/                    HTTP routes, errors, OpenAPI
│   ├── AGENTS.md
│   ├── README.md
│   └── docs/               public v1.1 contract, routes, development, work-items
├── frontend/               Next.js routes, components, services, types
│   ├── AGENTS.md
│   ├── README.md
│   └── docs/               implementation, API integration, development, work-items
├── tools/                  shared SPEC/ADR/planning/tasks + cross-role docs
├── tests/                  shared integration/backend/API tests
└── eval/                   quality benchmark artifacts (hiện report template)
```

## Trách nhiệm

| Role | Sở hữu | Phối hợp |
| --- | --- | --- |
| [Backend](../../backend/README.md) | Domain processing, validation, persistence, policy, worker | Models/contracts dùng chung API; inference/privacy/evaluation |
| [API](../../api/README.md) | HTTP input/output, status/errors, CORS, route binding, OpenAPI/docs | Gọi Backend; public compatibility và FE integration |
| [Frontend](../../frontend/README.md) | UI/routes, client services, typed models, interaction/state, docs | API consumer, auth UX, evidence/time/privacy presentation |

## Source-of-truth

`tools/specs`, `tools/adrs`, `tools/planning`, `tools/tasks` giữ canonical vì requirements/quyết định/task xuyên role. Role docs mô tả implementation, cách chạy, trách nhiệm và dẫn link tới task canonical; không copy thành task/spec khác. Work-items là index theo role, không phải backlog thứ hai.

Public schema code đang ở backend/models/contracts.py được API và services dùng chung. Nó thuộc Backend về runtime data model và API về public compatibility review. Không cần di chuyển classes/import chỉ để mọi file nhìn giống layout.

Tests API dùng cả backend worker/database nên giữ root tests. Eval và compose/CI là artifact dùng chung; role ownership đã ghi trong task. Chưa tạo runtime/team folder trống cho các role chưa được người dùng định nghĩa.

## Tài liệu đã chuyển

| Trước | Canonical hiện tại |
| --- | --- |
| docs/backend-runbook.md | [backend/docs/runbook.md](../../backend/docs/runbook.md) |
| docs/architecture_diagram.md | [backend/docs/architecture.md](../../backend/docs/architecture.md) |
| docs/backend-contract-v1.1.md | [api/docs/backend-contract-v1.1.md](../../api/docs/backend-contract-v1.1.md) |

Đường dẫn cũ giữ forwarding links; các link nội bộ trong tools dẫn thẳng đường canonical mới. Historical API contract migration table được giữ và bổ sung current integration note, không sửa lịch sử để giả mọi phần đã luôn triển khai.

Role của developer khác business role ENGINEER/REVIEWER. Tổ chức folder không tự tạo phân quyền đăng nhập hoặc chạy task implementation chưa hoàn thành.
