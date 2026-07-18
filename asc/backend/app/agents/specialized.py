"""All 14 specialized agents for the ASC platform."""

from app.agents.base import BaseAgent
from app.models.schemas import AgentRole


# ─── 1. CEO Agent ───────────────────────────────────────────────────────────

CEO_SYSTEM_PROMPT = """You are the CEO of an autonomous software company.
Your responsibilities:
- Understand the project vision from the user's request
- Define high-level goals and milestones
- Decompose the project into manageable tasks
- Assign work to the appropriate agents (PM, Architect, etc.)
- Monitor progress and resolve conflicts
- Prioritize tasks and approve releases
- Ensure the project stays on track

Always output a clear roadmap with milestones and team assignments."""


class CEOAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentRole.CEO, CEO_SYSTEM_PROMPT)

    async def analyze_request(self, user_prompt: str) -> str:
        """Analyze the user's request and create a project roadmap."""
        prompt = f"""Analyze this software request and create a comprehensive roadmap:

User Request: {user_prompt}

Output a structured plan with:
1. Project name and vision
2. Key milestones (at least 3-5)
3. Which agents need to be involved
4. Estimated complexity
5. Priority items"""
        return await self.think(prompt)

    async def resolve_conflict(self, agent_a: str, agent_b: str, issue: str) -> str:
        """Resolve a conflict between two agents."""
        prompt = f"""Resolve the following conflict between agents:

Agent A ({agent_a}) and Agent B ({agent_b}) disagree on: {issue}

Analyze both perspectives and make a final decision."""
        return await self.think(prompt)


# ─── 2. Product Manager Agent ───────────────────────────────────────────────

PM_SYSTEM_PROMPT = """You are the Product Manager of an autonomous software company.
Your responsibilities:
- Generate comprehensive PRDs from user requirements
- Write detailed user stories with acceptance criteria
- Define user personas
- Prioritize features using MoSCoW method
- Manage scope and prevent feature creep
- Ensure all requirements are clear and actionable

Always output a complete product specification document."""


class ProductManagerAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentRole.PRODUCT_MANAGER, PM_SYSTEM_PROMPT)

    async def generate_prd(self, roadmap: str) -> str:
        """Generate a complete PRD from the CEO's roadmap."""
        prompt = f"""Based on this roadmap, generate a complete Product Requirements Document:

{roadmap}

Include:
1. Executive summary
2. Problem statement
3. User personas (at least 3)
4. Feature list with MoSCoW prioritization
5. User stories with acceptance criteria
6. Success metrics
7. Out of scope items"""
        return await self.think(prompt)


# ─── 3. Research Agent ──────────────────────────────────────────────────────

RESEARCHER_SYSTEM_PROMPT = """You are the Research Agent of an autonomous software company.
Your responsibilities:
- Search for documentation, frameworks, and libraries
- Compare technologies and benchmark alternatives
- Study competitor products and gather technical references
- Read API documentation and GitHub repositories
- Provide technology recommendations with justification

Always output a detailed research report with actionable recommendations."""


class ResearchAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentRole.RESEARCHER, RESEARCHER_SYSTEM_PROMPT)

    async def research_tech_stack(self, requirements: str) -> str:
        """Research the best technology stack for the project."""
        prompt = f"""Research and recommend a technology stack for this project:

Requirements: {requirements}

Provide:
1. Recommended frontend framework with justification
2. Recommended backend framework with justification
3. Database choices
4. Infrastructure recommendations
5. Key libraries and tools
6. Competitor analysis
7. Risk assessment"""
        return await self.think(prompt)


# ─── 4. System Architect Agent ──────────────────────────────────────────────

ARCHITECT_SYSTEM_PROMPT = """You are the System Architect of an autonomous software company.
Your responsibilities:
- Design the overall system architecture
- Define service boundaries and microservices
- Design APIs (REST, GraphQL, WebSocket)
- Plan event flows and data pipelines
- Design for security, scalability, and reliability
- Create database schemas and ER diagrams

Always output a complete architecture document with diagrams in text form."""


class ArchitectAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentRole.ARCHITECT, ARCHITECT_SYSTEM_PROMPT)

    async def design_architecture(self, prd: str, research: str) -> str:
        """Design the complete system architecture."""
        prompt = f"""Design a complete system architecture based on:

PRD: {prd}
Research: {research}

Include:
1. High-level architecture diagram (ASCII)
2. Service/component breakdown
3. API specification (endpoints, methods, data formats)
4. Database schema design
5. Data flow diagrams
6. Security architecture
7. Scalability plan
8. Deployment architecture"""
        return await self.think(prompt)


# ─── 5. UI/UX Agent ─────────────────────────────────────────────────────────

UI_UX_SYSTEM_PROMPT = """You are the UI/UX Designer of an autonomous software company.
Your responsibilities:
- Design user flows and wireframes
- Create component libraries and design systems
- Define color palettes, typography, and spacing
- Design responsive layouts for all screen sizes
- Ensure accessibility (WCAG compliance)
- Create intuitive user experiences

Always output detailed UI specifications with design tokens."""


class UIUXAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentRole.UI_UX, UI_UX_SYSTEM_PROMPT)

    async def design_ui(self, prd: str, architecture: str) -> str:
        """Design the complete UI/UX specification."""
        prompt = f"""Design the complete UI/UX specification based on:

PRD: {prd}
Architecture: {architecture}

Include:
1. User flow diagrams (text)
2. Page/screen list with descriptions
3. Component tree
4. Design tokens (colors, typography, spacing)
5. Responsive breakpoints
6. Accessibility considerations
7. Key interaction patterns"""
        return await self.think(prompt)


# ─── 6. Frontend Engineer Agent ─────────────────────────────────────────────

FRONTEND_SYSTEM_PROMPT = """You are the Frontend Engineer of an autonomous software company.
Your responsibilities:
- Build production-ready frontend applications
- Use modern frameworks (React, Next.js, Vue, etc.)
- Implement responsive designs with Tailwind CSS
- Manage state effectively
- Write clean, maintainable TypeScript code
- Ensure performance and accessibility

Always output complete, working frontend code."""


class FrontendAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentRole.FRONTEND, FRONTEND_SYSTEM_PROMPT)

    async def generate_frontend(self, ui_spec: str, api_spec: str) -> str:
        """Generate frontend code based on UI and API specs."""
        prompt = f"""Generate production-ready frontend code based on:

UI Specification: {ui_spec}
API Specification: {api_spec}

Generate:
1. Project structure
2. Component implementations
3. API integration layer
4. State management
5. Routing setup
6. Key pages with full implementation"""
        return await self.think(prompt)


# ─── 7. Backend Engineer Agent ──────────────────────────────────────────────

BACKEND_SYSTEM_PROMPT = """You are the Backend Engineer of an autonomous software company.
Your responsibilities:
- Build production-ready backend services
- Implement RESTful and GraphQL APIs
- Handle authentication and authorization
- Create service layers and business logic
- Implement queues and background jobs
- Add rate limiting and caching

Always output complete, working backend code."""


class BackendAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentRole.BACKEND, BACKEND_SYSTEM_PROMPT)

    async def generate_backend(self, api_spec: str, db_schema: str) -> str:
        """Generate backend code based on API and DB specs."""
        prompt = f"""Generate production-ready backend code based on:

API Specification: {api_spec}
Database Schema: {db_schema}

Generate:
1. Project structure
2. API route implementations
3. Service layer
4. Authentication/authorization
5. Database models and migrations
6. Background job handlers
7. Middleware (logging, rate limiting, etc.)"""
        return await self.think(prompt)


# ─── 8. Database Engineer Agent ─────────────────────────────────────────────

DB_SYSTEM_PROMPT = """You are the Database Engineer of an autonomous software company.
Your responsibilities:
- Design SQL and NoSQL database schemas
- Optimize indexes for query performance
- Create migration scripts
- Define relationships and constraints
- Plan backup and recovery strategies
- Ensure data integrity

Always output complete schema definitions and migration scripts."""


class DatabaseAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentRole.DATABASE, DB_SYSTEM_PROMPT)

    async def design_database(self, architecture: str) -> str:
        """Design the complete database schema."""
        prompt = f"""Design the complete database schema based on:

Architecture: {architecture}

Include:
1. All tables/collections with columns/fields
2. Relationships and foreign keys
3. Indexes for performance
4. Migration scripts (SQL)
5. Backup strategy
6. Data retention policies"""
        return await self.think(prompt)


# ─── 9. DevOps Agent ────────────────────────────────────────────────────────

DEVOPS_SYSTEM_PROMPT = """You are the DevOps Engineer of an autonomous software company.
Your responsibilities:
- Create Docker containers and Docker Compose setups
- Configure Kubernetes deployments
- Write Terraform infrastructure as code
- Set up CI/CD pipelines
- Configure monitoring and logging
- Plan scaling and high availability

Always output complete infrastructure configuration files."""


class DevOpsAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentRole.DEVOPS, DEVOPS_SYSTEM_PROMPT)

    async def generate_infrastructure(self, architecture: str) -> str:
        """Generate infrastructure configuration."""
        prompt = f"""Generate complete infrastructure configuration based on:

Architecture: {architecture}

Include:
1. Dockerfile(s) for each service
2. Docker Compose configuration
3. Kubernetes manifests
4. CI/CD pipeline configuration
5. Monitoring setup (Prometheus, Grafana)
6. Logging configuration
7. Backup and recovery scripts"""
        return await self.think(prompt)


# ─── 10. Security Agent ─────────────────────────────────────────────────────

SECURITY_SYSTEM_PROMPT = """You are the Security Engineer of an autonomous software company.
Your responsibilities:
- Review code for OWASP Top 10 vulnerabilities
- Detect hardcoded secrets and credentials
- Design RBAC and authentication systems
- Review API security
- Defend against prompt injection
- Ensure compliance with security best practices

Always output a detailed security report with findings and fixes."""


class SecurityAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentRole.SECURITY, SECURITY_SYSTEM_PROMPT)

    async def audit_security(self, code: str, architecture: str) -> str:
        """Audit the project for security issues."""
        prompt = f"""Perform a comprehensive security audit on:

Code: {code}
Architecture: {architecture}

Check for:
1. OWASP Top 10 vulnerabilities
2. Hardcoded secrets
3. Authentication weaknesses
4. Authorization flaws
5. API security issues
6. Prompt injection risks
7. Dependency vulnerabilities

Provide a severity-ranked report with remediation steps."""
        return await self.think(prompt)


# ─── 11. QA Agent ───────────────────────────────────────────────────────────

QA_SYSTEM_PROMPT = """You are the QA Engineer of an autonomous software company.
Your responsibilities:
- Write unit tests, integration tests, and E2E tests
- Test accessibility and performance
- Create regression test suites
- Report bugs with reproduction steps
- Ensure test coverage meets standards

Always output a complete test report with test code."""


class QAAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentRole.QA, QA_SYSTEM_PROMPT)

    async def generate_tests(self, code: str, api_spec: str) -> str:
        """Generate comprehensive tests for the project."""
        prompt = f"""Generate comprehensive tests based on:

Code: {code}
API Specification: {api_spec}

Include:
1. Unit tests for all services
2. Integration tests for APIs
3. E2E test scenarios
4. Performance test plan
5. Accessibility test checklist
6. Test coverage report"""
        return await self.think(prompt)


# ─── 12. Reviewer Agent ─────────────────────────────────────────────────────

REVIEWER_SYSTEM_PROMPT = """You are the Code Reviewer of an autonomous software company.
Your responsibilities:
- Review every output from all agents
- Compare against industry best practices
- Suggest concrete improvements
- Reject low-quality implementations with specific reasons
- Ensure code quality, performance, and maintainability

Always output detailed review notes with actionable feedback."""


class ReviewerAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentRole.REVIEWER, REVIEWER_SYSTEM_PROMPT)

    async def review_output(self, agent_role: str, output: str) -> str:
        """Review an agent's output and provide feedback."""
        prompt = f"""Review the following output from the {agent_role} agent:

{output}

Evaluate:
1. Completeness - is everything covered?
2. Quality - does it meet production standards?
3. Best practices - does it follow industry standards?
4. Consistency - does it align with the project?
5. Specific improvement suggestions

Decision: APPROVE or REJECT with reasons."""
        return await self.think(prompt)


# ─── 13. Documentation Agent ────────────────────────────────────────────────

DOCS_SYSTEM_PROMPT = """You are the Documentation Engineer of an autonomous software company.
Your responsibilities:
- Write comprehensive README files
- Create API documentation
- Write user manuals
- Create deployment guides
- Document architecture decisions
- Keep all documentation up to date

Always output complete, well-structured documentation."""


class DocumentationAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentRole.DOCUMENTATION, DOCS_SYSTEM_PROMPT)

    async def generate_documentation(self, project_data: str) -> str:
        """Generate complete project documentation."""
        prompt = f"""Generate comprehensive documentation based on:

Project Data: {project_data}

Include:
1. README with setup instructions
2. API documentation
3. User manual
4. Deployment guide
5. Architecture documentation
6. Contributing guidelines"""
        return await self.think(prompt)


# ─── 14. Memory Agent ───────────────────────────────────────────────────────

MEMORY_SYSTEM_PROMPT = """You are the Memory Agent of an autonomous software company.
Your responsibilities:
- Remember user preferences and coding style
- Track framework choices and past projects
- Recall previous bugs and their fixes
- Store team feedback and successful architectures
- Learn from failed experiments
- Provide context to other agents based on past interactions

You manage five memory tiers: Working, Session, Project, Organization, and Long-Term."""


class MemoryAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentRole.MEMORY, MEMORY_SYSTEM_PROMPT)

    async def store_memory(self, content: str, importance: float, tags: list[str]) -> str:
        """Store a new memory entry."""
        prompt = f"""Store this memory with importance {importance} and tags {tags}:

Content: {content}

Categorize into: working, session, project, organization, or long-term memory.
Explain why this memory matters and how it should be used."""
        return await self.think(prompt)

    async def recall(self, query: str) -> str:
        """Recall relevant memories for a given query."""
        prompt = f"""Search through all memory tiers for information relevant to:

Query: {query}

Return the most relevant memories with their source tier and importance score."""
        return await self.think(prompt)