from django.test import TestCase
from django.utils import timezone
from decimal import Decimal

from apps.core.models import Department, Category, ESGConfiguration
from apps.environmental.models import EmissionFactor, CarbonEmission, SustainabilityGoal
from apps.dashboard.models import DepartmentESGScore

class ESGScoreEngineSignalTests(TestCase):
    def setUp(self):
        # Create department
        self.dept = Department.objects.create(name="Engineering", is_active=True)
        
        # Create default category
        self.category = Category.objects.create(name="Energy")
        
        # Create default emission factor
        self.factor = EmissionFactor.objects.create(
            name="Grid Electricity",
            unit="kWh",
            coefficient=Decimal("0.5000"),
            is_active=True
        )

        # Base configuration weights: Env: 50%, Social: 30%, Gov: 20%
        self.config = ESGConfiguration.objects.create(
            env_weight=Decimal("50.00"),
            social_weight=Decimal("30.00"),
            gov_weight=Decimal("20.00")
        )

    def test_carbon_emission_save_triggers_recalculation(self):
        # 2. Add a sustainability goal to verify environmental score changes (starts at 50 baseline if no goals)
        goal = SustainabilityGoal.objects.create(
            title="Reduce carbon footprint",
            target_metric="Scope 1 emissions",
            target_value=Decimal("100.00"),
            current_value=Decimal("80.00"),  # 80% progress
            unit="kg",
            deadline=timezone.now().date(),
            scope="dept",
            department=self.dept,
            status="active"
        )
        # Creating a goal triggers recalculation via post_save signals
        score_record = DepartmentESGScore.objects.get(department=self.dept)
        self.assertEqual(score_record.environmental_score, Decimal("80.00"))
        # Overall: Env(80)*0.5 + Social(40)*0.3 + Gov(65)*0.2 = 40 + 12 + 13 = 65.00
        self.assertEqual(score_record.overall_score, Decimal("65.00"))

        # 3. Create a carbon emission log
        emission = CarbonEmission.objects.create(
            department=self.dept,
            emission_source="Office lighting",
            activity_value=Decimal("100.00"),
            emission_factor=self.factor,
            auto_recalculate=True,
            reporting_period=timezone.now().date()
        )
        
        # Saving emission should recalculate
        score_record.refresh_from_db()
        self.assertEqual(score_record.environmental_score, Decimal("80.00"))

    def test_esg_configuration_weight_change_recalculates_all(self):
        # Setup baseline goal
        goal = SustainabilityGoal.objects.create(
            title="Reduce carbon footprint",
            target_metric="Scope 1 emissions",
            target_value=Decimal("100.00"),
            current_value=Decimal("60.00"),  # 60% progress
            unit="kg",
            deadline=timezone.now().date(),
            scope="dept",
            department=self.dept,
            status="active"
        )
        score_record = DepartmentESGScore.objects.get(department=self.dept)
        # Baseline score: Env(60)*0.5 + Social(40)*0.3 + Gov(65)*0.2 = 30 + 12 + 13 = 55
        self.assertEqual(score_record.overall_score, Decimal("55.00"))

        # Change weight settings
        self.config.env_weight = Decimal("30.00")
        self.config.social_weight = Decimal("40.00")
        self.config.gov_weight = Decimal("30.00")
        self.config.save()

        # Check overall score refreshed: Env(60)*0.3 + Social(40)*0.4 + Gov(65)*0.3 = 18 + 16 + 19.5 = 53.5
        score_record.refresh_from_db()
        self.assertEqual(score_record.overall_score, Decimal("53.50"))

    def test_emission_factor_change_cascades_emissions(self):
        # Create carbon emission log
        emission = CarbonEmission.objects.create(
            department=self.dept,
            emission_source="Office lighting",
            activity_value=Decimal("100.00"),
            emission_factor=self.factor,
            auto_recalculate=True,
            reporting_period=timezone.now().date()
        )
        self.assertEqual(emission.co2e_value, Decimal("50.00")) # 100 * 0.5

        # Update emission factor coefficient
        self.factor.coefficient = Decimal("0.7500")
        self.factor.save()

        # Verify carbon emission updated dynamically
        emission.refresh_from_db()
        self.assertEqual(emission.co2e_value, Decimal("75.00")) # 100 * 0.75
