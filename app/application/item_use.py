from app.domain.item_use import ItemUsePrepareRequest


def prepare_item_use(repository, **args):
    return repository.prepare(ItemUsePrepareRequest(**args))
