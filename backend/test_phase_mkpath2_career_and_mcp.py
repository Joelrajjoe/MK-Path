import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

from app.services.career_twin_service import CareerTwinService
from app.mcp.server import MCPToolRegistry
from app.database import db_manager

async def test_job_description_parsing():
    print("Testing Career Twin Job Description Analyzer...")
    sample_jd = """
    We are seeking a Senior Backend Engineer to design scalable microservices.
    Requirements:
    - 4+ years of Python, FastAPI, and PostgreSQL experience.
    - Deep understanding of Distributed Systems, Redis Caching, and Docker/Kubernetes.
    - Experience conducting unit testing and CI/CD automation.
    - Excellent system design communication and problem solving.
    """
    res = await CareerTwinService.analyze_job_description(sample_jd, role_hint="Senior Backend Engineer")
    assert res.role_title
    assert len(res.technical_skills) > 0 or len(res.extracted_skill_nodes) > 0
    print(f"  [OK] Parsed Role: {res.role_title} ({res.target_level})")
    print(f"  [OK] Extracted {len(res.extracted_skill_nodes)} Competency Nodes.")
    print("Job Description Analyzer tests passed!\n")

async def test_career_twin_readiness_calculation():
    print("Testing Career Twin Multi-Dimensional Readiness & Evidence Deficit...")
    dummy_goal = {
        "_id": "dummy_goal_001",
        "role": "Distributed Systems Engineer",
        "extracted_skills": [
            {"name": "Distributed Systems", "category": "technical", "required_level": 80.0, "career_importance": 2.0},
            {"name": "FastAPI", "category": "framework", "required_level": 75.0, "career_importance": 1.5},
            {"name": "Docker", "category": "tool", "required_level": 70.0, "career_importance": 1.0},
        ]
    }
    user_id = "test_clerk_user_career"
    report = await CareerTwinService.calculate_career_readiness(db_manager, user_id, dummy_goal)
    assert report.role == "Distributed Systems Engineer"
    assert isinstance(report.overall_readiness_score, float)
    assert len(report.explainable_breakdown) > 0
    assert report.recommended_next_action.get("type")
    print(f"  [OK] Overall Readiness: {report.overall_readiness_score}% (Status: {report.status})")
    print(f"  [OK] Next Action: {report.recommended_next_action.get('title')}")
    print("Career Twin Readiness tests passed!\n")

async def test_mcp_security_and_tools():
    print("Testing MK-Path MCP Tools & Cross-User Security...")
    user_a = "clerk_user_alice_123"
    user_b = "clerk_user_bob_456"

    # Test READ tool for Alice
    profile_a = await MCPToolRegistry.execute_tool(db_manager, user_a, "mkpath_get_learner_profile", {})
    assert profile_a["clerk_user_id"] == user_a
    print(f"  [OK] MCP Read Profile (Scoped to {user_a})")

    # Test Security: Cross-user violation / invalid identity
    try:
        await MCPToolRegistry.execute_tool(db_manager, "mock_unauthorized", "mkpath_get_learner_profile", {})
        assert False, "Should have raised PermissionError"
    except PermissionError:
        print("  [OK] Cross-User / Untrusted ID Access Successfully Blocked")

    # Test Audit Trail
    assert len(MCPToolRegistry.AUDIT_LOGS) >= 1
    last_log = MCPToolRegistry.AUDIT_LOGS[-1]
    assert last_log["tool_name"] == "mkpath_get_learner_profile"
    print("  [OK] MCP Audit Logging Verified")
    print("All MCP tests passed!\n")

async def main():
    print("=== RUNNING MK-PATH 2.0 PHASE 3 & 4 TEST SUITE ===\n")
    await test_job_description_parsing()
    await test_career_twin_readiness_calculation()
    await test_mcp_security_and_tools()
    print("=== ALL PHASE 3 & 4 TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    asyncio.run(main())
