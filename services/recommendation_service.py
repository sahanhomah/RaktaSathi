from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.db.models import Count, Max, Q, QuerySet
from django.utils import timezone

from donors.models import Donor
from donors.utils import BLOOD_COMPATIBILITY, can_donate_to, haversine_km
from requests.models import BloodRequest


DEFAULT_RELIABILITY_SCORE = 70.0
RELIABILITY_SCALE_FACTOR = 10.0
DONATION_ELIGIBILITY_DAYS = 90


@dataclass(frozen=True)
class DonorRecommendation:
	donor: Donor
	score: float
	distance: float
	blood_match_score: float
	distance_score: float
	eligibility_score: float
	availability_score: float
	reliability_score: float


class RecommendationService:
	"""Rank compatible donors for a blood request using a weighted score.

	The service keeps the recommendation logic isolated from the request workflow so
	it can be reused from views, tasks, or admin tooling without duplicating scoring
	code.
	"""

	def __init__(
		self,
		blood_request: BloodRequest,
		*,
		donor_queryset: QuerySet[Donor] | None = None,
		reference_time=None,
	):
		self.blood_request = blood_request
		self.reference_time = reference_time or timezone.now()
		self._donor_queryset = donor_queryset

	def get_eligible_donors(self) -> QuerySet[Donor]:
		"""Return donors whose blood group is compatible with the request."""

		if self._donor_queryset is not None:
			queryset = self._donor_queryset
		else:
			queryset = Donor.objects.all()

		compatible_blood_groups = [
			donor_group
			for donor_group, _label in Donor.BLOOD_GROUP_CHOICES
			if can_donate_to(donor_group, self.blood_request.blood_group)
		]

		queryset = queryset.filter(blood_group__in=compatible_blood_groups)

		requester_user_id = getattr(self.blood_request, 'requester_user_id', None)
		if requester_user_id:
			queryset = queryset.exclude(user_id=requester_user_id)

		# Keep the history data on the same queryset so scoring can run without extra
		# per-donor database hits.
		return queryset.select_related('user').annotate(
			accepted_requests_count=Count('accepted_requests', distinct=True),
			completed_donations_count=Count(
				'accepted_requests',
				filter=Q(accepted_requests__status='fulfilled'),
				distinct=True,
			),
			cancelled_requests_count=Count(
				'accepted_requests',
				filter=Q(accepted_requests__status='cancelled'),
				distinct=True,
			),
			last_completed_donation_at=Max(
				'accepted_requests__fulfilled_at',
				filter=Q(accepted_requests__status='fulfilled'),
			),
		)

	def calculate_blood_match_score(self, donor: Donor) -> float:
		"""Exact matches score highest; other compatible donors are slightly lower."""

		if donor.blood_group == self.blood_request.blood_group:
			return 100.0
		if can_donate_to(donor.blood_group, self.blood_request.blood_group):
			return 90.0
		return 0.0

	def calculate_distance_score(self, distance_km: float) -> float:
		"""Convert distance into a 0-100 score using a simple stepped scale."""

		if distance_km <= 2:
			return 100.0
		if distance_km <= 5:
			return 80.0
		if distance_km <= 10:
			return 60.0
		if distance_km <= 20:
			return 40.0
		return 20.0

	def calculate_eligibility_score(self, donor: Donor) -> float:
		"""Score donors who are eligible to donate today at full value."""

		last_donation_at = getattr(donor, 'last_completed_donation_at', None)
		if last_donation_at is None:
			return 100.0

		age = self.reference_time - last_donation_at
		if age.days >= DONATION_ELIGIBILITY_DAYS:
			return 100.0
		return 0.0

	def calculate_availability_score(self, donor: Donor) -> float:
		"""Use the existing availability fields without changing the donor model."""

		if donor.is_available:
			return 100.0
		if donor.availability_reenable_at and donor.availability_reenable_at > self.reference_time:
			return 50.0
		return 0.0

	def calculate_reliability_score(self, donor: Donor) -> float:
		"""Normalize donor history into a 0-100 reliability score.

		The raw signal rewards accepted and completed requests while penalizing
		cancellations. When a donor has no historical data yet, a neutral default is
		used so new donors are not unfairly disadvantaged.
		"""

		accepted_requests = int(getattr(donor, 'accepted_requests_count', 0) or 0)
		completed_donations = int(getattr(donor, 'completed_donations_count', 0) or 0)
		cancelled_requests = int(getattr(donor, 'cancelled_requests_count', 0) or 0)

		if accepted_requests == 0 and completed_donations == 0 and cancelled_requests == 0:
			return DEFAULT_RELIABILITY_SCORE

		raw_reliability = max(0, (accepted_requests * 2) + completed_donations - cancelled_requests)
		normalized = min(100.0, raw_reliability * RELIABILITY_SCALE_FACTOR)
		return float(normalized)

	def calculate_recommendation_score(self, donor: Donor, distance_km: float) -> float:
		"""Combine all component scores using the requested weighted formula."""

		blood_match_score = self.calculate_blood_match_score(donor)
		distance_score = self.calculate_distance_score(distance_km)
		eligibility_score = self.calculate_eligibility_score(donor)
		availability_score = self.calculate_availability_score(donor)
		reliability_score = self.calculate_reliability_score(donor)

		total_score = (
			blood_match_score * 0.35
			+ distance_score * 0.30
			+ eligibility_score * 0.15
			+ availability_score * 0.10
			+ reliability_score * 0.10
		)
		return round(float(total_score), 2)

	def rank_donors(self) -> list[dict[str, Any]]:
		"""Return compatible donors sorted from highest score to lowest."""

		ranked: list[dict[str, Any]] = []

		for donor in self.get_eligible_donors():
			distance_km = haversine_km(
				float(self.blood_request.latitude),
				float(self.blood_request.longitude),
				float(donor.latitude),
				float(donor.longitude),
			)
			blood_match_score = self.calculate_blood_match_score(donor)
			distance_score = self.calculate_distance_score(distance_km)
			eligibility_score = self.calculate_eligibility_score(donor)
			availability_score = self.calculate_availability_score(donor)
			reliability_score = self.calculate_reliability_score(donor)
			total_score = round(
				blood_match_score * 0.35
				+ distance_score * 0.30
				+ eligibility_score * 0.15
				+ availability_score * 0.10
				+ reliability_score * 0.10,
				2,
			)

			ranked.append(
				{
					'donor': donor,
					'score': total_score,
					'distance': round(distance_km, 2),
					'blood_match_score': blood_match_score,
					'distance_score': distance_score,
					'eligibility_score': eligibility_score,
					'availability_score': availability_score,
					'reliability_score': reliability_score,
				},
			)

		ranked.sort(key=lambda item: (-item['score'], item['distance'], item['donor'].id))
		return ranked
