"""
E2E Regression Test Compiler Agent
Analyzes story-based test cases and compiles them into Feature-based E2E regression test cases
Ensures new development doesn't break existing functionalities
"""
import json
import logging
from typing import List, Dict, Tuple, Set
from openai import OpenAI
from models import TestCase, TestStep
from config.settings import settings, TestStatus

logger = logging.getLogger(__name__)

class ApplicationAnalyzer:
    """
    Analyzes story-based test cases to understand application features
    Identifies feature areas, user flows, and interdependencies
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
    
    def analyze_test_cases(self, test_cases: List[TestCase]) -> Dict:
        """
        Analyze test cases to understand application features and flows
        
        Args:
            test_cases: List of story-based test cases
            
        Returns:
            Dictionary with application analysis
        """
        logger.info("\n[E2E Compiler] Analyzing application from test cases...")
        logger.info(f"Total test cases to analyze: {len(test_cases)}")
        
        analysis = {
            "features": [],
            "user_flows": [],
            "dependencies": [],
            "critical_paths": [],
            "data_dependencies": [],
            "integration_points": []
        }
        
        if not test_cases:
            return analysis
        
        # Extract features from test cases
        features = self._extract_features(test_cases)
        analysis["features"] = features
        
        # Identify user flows and sequences
        flows = self._identify_user_flows(test_cases)
        analysis["user_flows"] = flows
        
        # Analyze dependencies between test cases
        dependencies = self._analyze_dependencies(test_cases)
        analysis["dependencies"] = dependencies
        
        # Identify critical paths
        critical_paths = self._identify_critical_paths(test_cases)
        analysis["critical_paths"] = critical_paths
        
        # Analyze data dependencies
        data_deps = self._analyze_data_dependencies(test_cases)
        analysis["data_dependencies"] = data_deps
        
        # Identify integration points
        integration = self._identify_integration_points(test_cases)
        analysis["integration_points"] = integration
        
        logger.info("Analysis complete:")
        logger.info(f"  - Features identified: {len(features)}")
        logger.info(f"  - User flows identified: {len(flows)}")
        logger.info(f"  - Dependencies mapped: {len(dependencies)}")
        logger.info(f"  - Critical paths identified: {len(critical_paths)}")
        
        return analysis
    
    def _extract_features(self, test_cases: List[TestCase]) -> List[Dict]:
        """Extract distinct features from test cases"""
        features = {}
        
        for test_case in test_cases:
            feature = test_case.test_scenario or "General"
            
            if feature not in features:
                features[feature] = {
                    "name": feature,
                    "test_count": 0,
                    "test_cases": [],
                    "description": ""
                }
            
            features[feature]["test_count"] += 1
            features[feature]["test_cases"].append(test_case.test_case_name)
        
        return list(features.values())
    
    def _identify_user_flows(self, test_cases: List[TestCase]) -> List[Dict]:
        """Identify sequential user flows from test cases"""
        flows = []
        
        # Group by scenario
        scenarios = {}
        for test_case in test_cases:
            scenario = test_case.test_scenario or "Default"
            if scenario not in scenarios:
                scenarios[scenario] = []
            scenarios[scenario].append(test_case)
        
        # Create flows from scenarios
        for scenario, cases in scenarios.items():
            if len(cases) > 1:
                flow = {
                    "name": f"{scenario} Flow",
                    "steps": len(cases),
                    "test_cases": [tc.test_case_name for tc in cases],
                    "type": "multi-step"
                }
            else:
                flow = {
                    "name": f"{scenario} Flow",
                    "steps": 1,
                    "test_cases": [tc.test_case_name for tc in cases],
                    "type": "single-step"
                }
            
            flows.append(flow)
        
        return flows
    
    def _analyze_dependencies(self, test_cases: List[TestCase]) -> List[Dict]:
        """Analyze dependencies between test cases"""
        dependencies = []
        
        # Look for test cases that depend on previous outcomes
        for i, test_case in enumerate(test_cases):
            # Check if test mentions prerequisites or dependencies
            remarks = (test_case.remarks or "").lower()
            
            if any(word in remarks for word in ["after", "depends", "requires", "prerequisite"]):
                dependency = {
                    "dependent": test_case.test_case_name,
                    "description": remarks,
                    "type": "sequential"
                }
                dependencies.append(dependency)
        
        return dependencies
    
    def _identify_critical_paths(self, test_cases: List[TestCase]) -> List[Dict]:
        """Identify critical business paths from test cases"""
        critical_paths = []
        
        # Mark tests with priority 1 as critical
        for test_case in test_cases:
            # Extract priority if available
            remarks = test_case.remarks or ""
            if "critical" in remarks.lower() or "priority" in remarks.lower():
                path = {
                    "name": test_case.test_case_name,
                    "scenario": test_case.test_scenario,
                    "criticality": "high",
                    "impact": "business critical"
                }
                critical_paths.append(path)
        
        return critical_paths
    
    def _analyze_data_dependencies(self, test_cases: List[TestCase]) -> List[Dict]:
        """Analyze data flow and dependencies"""
        data_deps = []
        
        for test_case in test_cases:
            if test_case.test_data:
                dep = {
                    "test_case": test_case.test_case_name,
                    "requires_data": True,
                    "data_scope": "story-specific"
                }
                data_deps.append(dep)
        
        return data_deps
    
    def _identify_integration_points(self, test_cases: List[TestCase]) -> List[Dict]:
        """Identify integration points between features"""
        integration_points = []
        
        # Analyze test steps for integration indicators
        integration_keywords = ["api", "database", "service", "external", "integration", "interface"]
        
        for test_case in test_cases:
            for step in test_case.steps:
                step_text = (step.description + " " + step.expected_results).lower()
                
                if any(keyword in step_text for keyword in integration_keywords):
                    point = {
                        "test_case": test_case.test_case_name,
                        "step": step.step_no,
                        "description": step.description,
                        "type": "integration"
                    }
                    integration_points.append(point)
        
        return integration_points


class E2ERegressionTestCompiler:
    """
    Compiles story-based test cases into E2E regression test scenarios
    Creates comprehensive regression test suites for features
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.analyzer = ApplicationAnalyzer()
    
    def compile_regression_tests(self, test_cases: List[TestCase]) -> Tuple[List[TestCase], Dict]:
        """
        Compile story-based test cases into E2E regression test suite
        
        Args:
            test_cases: List of story-based test cases
            
        Returns:
            Tuple of (regression_test_cases, compilation_report)
        """
        logger.info("\n" + "="*70)
        logger.info("E2E REGRESSION TEST COMPILATION")
        logger.info("="*70)
        
        if not test_cases:
            logger.warning("No test cases to compile for regression testing")
            return [], {}
        
        # Step 1: Analyze application
        logger.info("\n[Step 1] Analyzing application from test cases...")
        analysis = self.analyzer.analyze_test_cases(test_cases)
        
        # Step 2: Identify feature groups
        logger.info("\n[Step 2] Grouping tests by features...")
        feature_groups = self._group_by_feature(test_cases, analysis)
        
        # Step 3: Generate E2E scenarios
        logger.info("\n[Step 3] Generating E2E regression scenarios...")
        regression_tests = []
        
        for feature_name, feature_tests in feature_groups.items():
            logger.info(f"\n  Processing feature: {feature_name}")
            
            # Create E2E test for this feature
            e2e_tests = self._create_feature_e2e_tests(
                feature_name, 
                feature_tests, 
                analysis
            )
            
            regression_tests.extend(e2e_tests)
            logger.info(f"  Generated {len(e2e_tests)} E2E test(s) for {feature_name}")
        
        # Step 4: Create cross-feature integration tests
        logger.info("\n[Step 4] Creating cross-feature integration tests...")
        integration_tests = self._create_integration_tests(test_cases, feature_groups)
        regression_tests.extend(integration_tests)
        logger.info(f"  Generated {len(integration_tests)} integration test(s)")
        
        # Step 5: Create critical path regression tests
        logger.info("\n[Step 5] Creating critical path tests...")
        critical_tests = self._create_critical_path_tests(analysis)
        regression_tests.extend(critical_tests)
        logger.info(f"  Generated {len(critical_tests)} critical path test(s)")
        
        # Generate report
        report = {
            "total_story_tests": len(test_cases),
            "total_regression_tests": len(regression_tests),
            "features_identified": len(feature_groups),
            "analysis": analysis,
            "feature_groups": {k: [t.test_case_name for t in v] for k, v in feature_groups.items()},
            "regression_test_count": {
                "feature_e2e": len(regression_tests) - len(integration_tests) - len(critical_tests),
                "integration": len(integration_tests),
                "critical_path": len(critical_tests)
            }
        }
        
        logger.info("\n" + "="*70)
        logger.info("COMPILATION SUMMARY")
        logger.info("="*70)
        logger.info(f"Story-based test cases: {report['total_story_tests']}")
        logger.info(f"Regression test cases generated: {report['total_regression_tests']}")
        logger.info(f"Features identified: {report['features_identified']}")
        logger.info(f"  - Feature E2E tests: {report['regression_test_count']['feature_e2e']}")
        logger.info(f"  - Integration tests: {report['regression_test_count']['integration']}")
        logger.info(f"  - Critical path tests: {report['regression_test_count']['critical_path']}")
        logger.info("="*70 + "\n")
        
        return regression_tests, report
    
    def _group_by_feature(self, test_cases: List[TestCase], 
                         analysis: Dict) -> Dict[str, List[TestCase]]:
        """Group test cases by feature"""
        feature_groups = {}
        
        for test_case in test_cases:
            feature = test_case.test_scenario or "General"
            
            if feature not in feature_groups:
                feature_groups[feature] = []
            
            feature_groups[feature].append(test_case)
        
        return feature_groups
    
    def _create_feature_e2e_tests(self, feature_name: str, 
                                 feature_tests: List[TestCase],
                                 analysis: Dict) -> List[TestCase]:
        """
        Create comprehensive E2E test scenarios for a feature
        Combines multiple test cases into end-to-end user journeys
        """
        e2e_tests = []
        
        # Test 1: Happy path through all feature tests
        if feature_tests:
            happy_path_test = self._create_happy_path_e2e(feature_name, feature_tests)
            e2e_tests.append(happy_path_test)
        
        # Test 2: Feature with variations and edge cases
        if len(feature_tests) > 1:
            edge_case_test = self._create_edge_case_e2e(feature_name, feature_tests)
            e2e_tests.append(edge_case_test)
        
        # Test 3: Error handling and recovery
        error_test = self._create_error_recovery_e2e(feature_name, feature_tests)
        e2e_tests.append(error_test)
        
        return e2e_tests
    
    def _create_happy_path_e2e(self, feature_name: str, 
                              test_cases: List[TestCase]) -> TestCase:
        """Create happy path E2E test"""
        test_case = TestCase()
        test_case.test_scenario = f"{feature_name} - Regression Suite"
        test_case.test_case_name = f"E2E: {feature_name} - Happy Path"
        test_case.remarks = "E2E Regression Test - Full feature workflow"
        
        # Combine steps from all test cases
        step_no = 1
        for tc in test_cases:
            for step in tc.steps:
                new_step = TestStep(
                    step_no=step_no,
                    description=f"[{tc.test_case_name}] {step.description}",
                    expected_results=step.expected_results
                )
                test_case.steps.append(new_step)
                step_no += 1
        
        # Add verification step
        final_step = TestStep(
            step_no=step_no,
            description=f"Verify {feature_name} feature is fully functional",
            expected_results="All feature components working correctly"
        )
        test_case.steps.append(final_step)
        
        return test_case
    
    def _create_edge_case_e2e(self, feature_name: str, 
                             test_cases: List[TestCase]) -> TestCase:
        """Create edge case E2E test"""
        test_case = TestCase()
        test_case.test_scenario = f"{feature_name} - Regression Suite"
        test_case.test_case_name = f"E2E: {feature_name} - Edge Cases"
        test_case.remarks = "E2E Regression Test - Edge cases and variations"
        
        # Include edge case variations
        step_no = 1
        for i, tc in enumerate(test_cases):
            # Add primary step
            if tc.steps:
                step = tc.steps[0]
                new_step = TestStep(
                    step_no=step_no,
                    description=f"[{tc.test_case_name}] {step.description} - Edge case variation",
                    expected_results=step.expected_results
                )
                test_case.steps.append(new_step)
                step_no += 1
        
        return test_case
    
    def _create_error_recovery_e2e(self, feature_name: str, 
                                  test_cases: List[TestCase]) -> TestCase:
        """Create error handling and recovery E2E test"""
        test_case = TestCase()
        test_case.test_scenario = f"{feature_name} - Regression Suite"
        test_case.test_case_name = f"E2E: {feature_name} - Error Recovery"
        test_case.remarks = "E2E Regression Test - Error scenarios and recovery"
        
        steps = [
            TestStep(
                step_no=1,
                description=f"Attempt {feature_name} with invalid inputs",
                expected_results="System displays appropriate error message"
            ),
            TestStep(
                step_no=2,
                description=f"Verify error logging for {feature_name}",
                expected_results="Error logged in system logs"
            ),
            TestStep(
                step_no=3,
                description=f"Recover and retry {feature_name} with valid inputs",
                expected_results="Feature executes successfully after recovery"
            ),
            TestStep(
                step_no=4,
                description=f"Verify system state after {feature_name} error/recovery",
                expected_results="System in consistent state, no data corruption"
            )
        ]
        
        test_case.steps = steps
        return test_case
    
    def _create_integration_tests(self, test_cases: List[TestCase], 
                                 feature_groups: Dict) -> List[TestCase]:
        """Create cross-feature integration tests"""
        integration_tests = []
        
        # Create tests for feature interactions
        feature_list = list(feature_groups.keys())
        
        if len(feature_list) > 1:
            # Test interactions between major features
            for i, feature1 in enumerate(feature_list[:-1]):
                feature2 = feature_list[i + 1]
                
                test_case = TestCase()
                test_case.test_scenario = "Cross-Feature Integration"
                test_case.test_case_name = f"E2E: {feature1} ↔ {feature2} Integration"
                test_case.remarks = "E2E Regression Test - Feature integration"
                
                steps = [
                    TestStep(
                        step_no=1,
                        description=f"Complete {feature1} workflow",
                        expected_results=f"{feature1} completes successfully"
                    ),
                    TestStep(
                        step_no=2,
                        description=f"Transition to {feature2} workflow",
                        expected_results="Data flows correctly between features"
                    ),
                    TestStep(
                        step_no=3,
                        description=f"Complete {feature2} workflow",
                        expected_results=f"{feature2} completes successfully"
                    ),
                    TestStep(
                        step_no=4,
                        description=f"Verify {feature1} state remains consistent",
                        expected_results=f"{feature1} state unchanged by {feature2}"
                    )
                ]
                
                test_case.steps = steps
                integration_tests.append(test_case)
        
        return integration_tests
    
    def _create_critical_path_tests(self, analysis: Dict) -> List[TestCase]:
        """Create regression tests for critical business paths"""
        critical_tests = []
        
        # Create critical path test if critical paths were identified
        if analysis.get("critical_paths"):
            test_case = TestCase()
            test_case.test_scenario = "Critical Paths Regression"
            test_case.test_case_name = "E2E: Critical Business Path"
            test_case.remarks = "E2E Regression Test - Critical business path"
            
            steps = [
                TestStep(
                    step_no=1,
                    description="Execute critical business path from start to end",
                    expected_results="All critical steps execute successfully"
                ),
                TestStep(
                    step_no=2,
                    description="Verify data integrity throughout path",
                    expected_results="No data loss or corruption"
                ),
                TestStep(
                    step_no=3,
                    description="Verify performance metrics",
                    expected_results="Response times within acceptable range"
                ),
                TestStep(
                    step_no=4,
                    description="Verify system stability after critical path",
                    expected_results="System ready for next operation"
                )
            ]
            
            test_case.steps = steps
            critical_tests.append(test_case)
        
        return critical_tests
    
    def create_regression_test_suite_report(self, 
                                           story_tests: List[TestCase],
                                           regression_tests: List[TestCase],
                                           compilation_report: Dict) -> str:
        """Create detailed report on regression test compilation"""
        report = "\n" + "="*70 + "\n"
        report += "E2E REGRESSION TEST SUITE COMPILATION REPORT\n"
        report += "="*70 + "\n\n"
        
        report += "OVERVIEW\n"
        report += "-"*70 + "\n"
        report += f"Story-based Test Cases: {len(story_tests)}\n"
        report += f"E2E Regression Test Cases: {len(regression_tests)}\n"
        report += f"Regression Test Coverage Ratio: {len(regression_tests) / len(story_tests):.2f}x\n\n"
        
        report += "TEST DISTRIBUTION\n"
        report += "-"*70 + "\n"
        report += f"Feature E2E Tests: {compilation_report['regression_test_count'].get('feature_e2e', 0)}\n"
        report += f"Integration Tests: {compilation_report['regression_test_count'].get('integration', 0)}\n"
        report += f"Critical Path Tests: {compilation_report['regression_test_count'].get('critical_path', 0)}\n\n"
        
        report += "FEATURES IDENTIFIED\n"
        report += "-"*70 + "\n"
        for feature, tests in compilation_report.get('feature_groups', {}).items():
            report += f"{feature}: {len(tests)} story-based tests\n"
        
        report += "\n" + "="*70 + "\n"
        
        return report
