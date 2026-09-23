from app.domain.redemptions import RedemptionReceipt, RedemptionRequest
from app.repositories.protocols import RedemptionMutationRepository


def redeem_purchase_v2(repository: RedemptionMutationRepository, **args) -> RedemptionReceipt:
    return repository.redeem_purchase(RedemptionRequest(**args))
