from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import modal
from modal import Image
from src.services.dlt.destination_type import (
    DestinationType,
)
from src.services.dlt.filesystem import (
    convert_bucket_url_to_pipeline_name,
    to_filesystem_gcs,
    to_filesystem_local,
)
from src.services.local.filesystem import (
    DestinationFileData,
    SourceFileData,
    get_file_data_from_input_folder,
    get_json_data_from_file_data,
)

if TYPE_CHECKING:
    from collections.abc import Iterator


from src.services.octolens.mentions.etl.webhook import Webhook


class WebhookModel(Webhook): ...


DLT_DESTINATION_URL_GCP: str = "gs://chalk-ai-devx-octolens-mentions-etl"
DEVX_PIPELINE_NAME: str = convert_bucket_url_to_pipeline_name(
    DLT_DESTINATION_URL_GCP,
)
MODAL_SECRET_COLLECTION_NAME: str = "devx-growth-gcp"  # trunk-ignore(ruff/S105)

image: Image = modal.Image.debian_slim().pip_install(
    "fastapi[standard]",
    "gcsfs",  # https://github.com/fsspec/gcsfs
    "uuid7",
)
image.add_local_python_source(
    *[
        "src",
    ],
)
app = modal.App(
    name=DEVX_PIPELINE_NAME,
    image=image,
)


def to_filesystem(
    data: Iterator[DestinationFileData],
    bucket_url: str = DLT_DESTINATION_URL_GCP,
) -> str:
    match bucket_url:
        case str() as url if url.startswith("gs://"):
            to_filesystem_gcs(
                data=data,
            )

        case _:
            bucket_url_path: Path = Path(bucket_url)
            print(bucket_url_path)
            bucket_url_path.mkdir(
                parents=True,
                exist_ok=True,
            )
            to_filesystem_local(
                data=data,
            )

    return "Successfully uploaded"


@app.function(
    secrets=[
        modal.Secret.from_name(
            name=MODAL_SECRET_COLLECTION_NAME,
        ),
    ],
    region="us-east4",  # This feature is available on the Team and Enterprise plans, read more at https://modal.com/docs/guide/region-selection
    allow_concurrent_inputs=1000,
    enable_memory_snapshot=True,
)
@modal.web_endpoint(
    method="POST",
    docs=True,
)
def web(
    webhook: WebhookModel,
) -> str:
    def generate_destination_file_data(
        webhook: WebhookModel,
        bucket_url: str,
    ) -> Iterator[DestinationFileData]:
        yield DestinationFileData(
            json=webhook.etl_get_json(),
            path=f"{bucket_url}/{webhook.etl_get_file_name()}",
        )

    if not webhook.etl_is_valid_webhook():
        return webhook.etl_get_invalid_webhook_error_msg()

    data: Iterator[DestinationFileData] = generate_destination_file_data(
        webhook=webhook,
        bucket_url=DLT_DESTINATION_URL_GCP,
    )
    return to_filesystem(
        data=data,
        bucket_url=DLT_DESTINATION_URL_GCP,
    )


@app.local_entrypoint()
def local(
    input_folder: str,
    destination_type: str,
) -> None:
    destination_type_enum: DestinationType = DestinationType(destination_type)
    bucket_url: str
    match destination_type_enum:
        case DestinationType.LOCAL:
            bucket_url = DestinationType.get_bucket_url_for_local(
                pipeline_name=DEVX_PIPELINE_NAME,
            )

        case DestinationType.GCP:
            bucket_url = DLT_DESTINATION_URL_GCP

        case _:
            error_msg: str = f"Invalid destination type: {destination_type_enum}"
            raise ValueError(error_msg)

    file_data: Iterator[SourceFileData] = get_file_data_from_input_folder(
        input_folder=input_folder,
        base_model=WebhookModel,  # trunk-ignore(pyright/reportArgumentType)
    )
    data: Iterator[DestinationFileData] = get_json_data_from_file_data(
        file_data=file_data,
        bucket_url=bucket_url,
    )
    response: str = to_filesystem(
        data=data,
        bucket_url=bucket_url,
    )
    print(response)
