# This is a token classification model trained with two loss functions:
# 1. Cross entropy loss for the dataset tokens
# 2. Some other loss for comparing embeddings of the context tokens
#
# See https://github.com/Coleridge-Initiative/rc-kaggle-models/blob/main/1st%20ZALO%20FTW/MODEL_SUMMARY.pdf
# for more details.



from functools import partial
from itertools import islice
import logging
from typing import Any, Dict, Optional

import datasets as ds
import pandas as pd
import torch
import transformers as tfs
from pytorch_metric_learning import metric_losses
from tqdm import tqdm
from transformers import AutoConfig, AutoModelForTokenClassification, AutoTokenizer

from datasets.utils.logging import disable_progress_bar
disable_progress_bar()


from src.data.repository import Repository
import src.models.base_model as bm

logger = logging.getLogger("token_classification_model")

def validate_config(config: Dict[str, Any]) -> None:

    expected_keys = {
        "model_tokenizer_name",
        "tokenizer_kwargs",
        "model_kwargs",
        "optimizer",
        "optimizer_kwargs",
    }

    missing_keys = expected_keys - set(config.keys())
    assert not missing_keys, f"Missing keys: {missing_keys}"

def train(
    repository: Repository,
    config: Dict[str, Any],
    training_logger: Optional[bm.SupportsLogging] = None,
) -> None:
        validate_config(config)

        training_logger.log_parameters(
            {
                "model_tokenizer_name": config["model_tokenizer_name"],
                "optimizer": config["optimizer"],
            }
            | config["tokenizer_kwargs"]
            | config["model_kwargs"]
            | config["optimizer_kwargs"]
        )



def validate(repository: Repository, config: Dict[str, Any]) -> None:

    validate_config(config)


def prepare_batch(
        tokenizer: tfs.tokenization_utils_base.PreTrainedTokenizerBase,
        data_collator: tfs.data.data_collator.DataCollatorMixin,
        lbl_to_id: Dict[str, int],
        batch: pd.DataFrame
    ) -> Dict[str, torch.Tensor]:

    ner_to_id_f = partial(convert_sample_ner_tages_to_ids, lbl_to_id)
    tokenize_f = partial(
        tokenize_and_align_labels,
        partial(tokenizer, is_split_into_words=True, truncation=True),
    )


    transformed_batch = ds.Dataset.from_pandas(
         batch.drop(columns=["tags"]).rename(columns={"ner_tags": "labels"})
    ).map(
        ner_to_id_f,
        batched=True
    ).map(
        tokenize_f,
        batched=True,
        remove_columns=["text"]
    )

    return data_collator(list(transformed_batch))

class GenericModel1(bm.Model):

    def inference(self, config: Dict[str, Any], df: pd.DataFrame) -> pd.DataFrame:
        return super().inference(config, df)


    def train(self, repository: Repository, config: Dict[str, Any], training_logger: bm.SupportsLogging) -> None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        (
            model,
            tokenizer,
            collator,
            optimizer,
            scheduler,
            metric_loss,
            metric_optimizer,
            metric_scheduler
        ) = self.get_model_objects(config, include_optimizer=True)

        training_iter = repository.get_training_data(
            batch_size=config["batch_size"],
            balance_labels = config.get("balance_labels", False)
        )

        step  = config.get("start_step", 0)
        for epoch in range(config["epochs"]):
            for batch in tqdm(training_iter, desc=f"Training Epoch {epoch}"):
                model.train()
                metric_loss.train()

                batch = {k:v.to(device) for k,v in batch.items()}
                batch_query, batch_support,query_labels = prepare_batch(tokenizer, collator, batch)

                optimizer.zero_grad()
                metric_optimizer.zero_grad()




                # bs = support batch size
                # bq = query batch size
                # seq_len = sequence length
                # emb_dim = embedding dimension

                # Variables are named to match the document from the first place
                # solution document, linked above, Section 2.3.3.3. Embeddings extraction


                # First process the support set ================================
                output_support = model(**batch_support)
                support_labels = batch_support["labels"] # [bs, 1]
                support_hidden_states = output_support.last_hidden_state # [bs, seq_len, emb_dim]
                # might be support_hidden_states = output_support.hidden_states[-1]


                # the first token is the CLS token which is the support embedding
                support_embedding = support_hidden_states[:, 0, :] # [bs, emb_dim]

                # NEED TO ALSO ZERO OUT BY ATTENTION MASK

                # zero-out non mask tokens
                #                         [bs, seq_len, emb_dim] * [bs, seq_len, 1]
                support_mask_tokens_seq = support_hidden_states * batch_query["float_mask_mask"].unsqueeze(-1) # [bs, seq_len, emb_dime]
                support_mask_token_sum = support_mask_tokens_seq.sum(dim=1) # [bs, emb_dim]
                support_mask_token_n = batch_query["float_mask_mask"].sum(dim=1, keepdim=True) # [bs, 1]
                mask_embedding = support_mask_token_sum / support_mask_token_n # [bs, emb_dim]

                # flip the mask and zero-out mask tokens
                suppport_non_mask_tokens_seq = support_hidden_states * (1 - batch_query["float_mask_mask"]).unsqueeze(-1) # [bs, seq_len, emb_dime]
                support_non_mask_token_sum = suppport_non_mask_tokens_seq.sum(dim=1) # [bs, emb_dim]
                support_non_mask_token_n = (1 - batch_query["float_mask_mask"]).sum(dim=1, keepdim=True) # [bs, 1]
                non_mask_embedding = support_non_mask_token_sum / support_non_mask_token_n # [bs, emb_dim]
                # ==============================================================

                # Second process the query set =================================
                output_query = model(**batch_query)
                query_hidden_states = output_query.last_hidden_state # [bq, seq_len, emb_dim]
                # might be query_hidden_states = output_query.hidden_states[-1]

                query_mask_tokens_seq = query_hidden_states * batch_query["float_mask_mask"].unsqueeze(-1) # [bq, seq_len, emb_dime]
                query_mask_token_sum = query_mask_tokens_seq.sum(dim=1) # [bq, emb_dim]
                query_mask_token_n = batch_query["float_mask_mask"].sum(dim=1, keepdim=True) # [bq, 1]
                label_embedding = query_mask_token_sum / query_mask_token_n # [bq, emb_dim]

                # flip the mask and zero-out mask tokens
                query_non_mask_tokens_seq = query_hidden_states * (1 - batch_query["float_mask_mask"]).unsqueeze(-1) # [bq, seq_len, emb_dime]
                query_non_mask_token_sum = query_non_mask_tokens_seq.sum(dim=1) # [bq, emb_dim]
                query_non_mask_token_n = (1 - batch_query["float_mask_mask"]).sum(dim=1, keepdim=True) # [bq, 1]
                non_label_embedding = query_non_mask_token_sum / query_non_mask_token_n # [bq, emb_dim]
                # ==============================================================


                # Third compute the loss =======================================
                # From the document, Section 2.3.3.3. Applying criterions
                # We apply ArcFace loss to two pairs of embeddings:
                #   ● SUPPORT MASK and QUERY LABEL (if available) are considered class 0.
                #   ● SUPPORT non-MASK and QUERY non-LABEL are considered class 1.
                # We also apply ArcFace loss for these embeddings:
                #   ● SUPPORT embeddings are considered class 0
                #   ● Positive QUERY embeddings are considered class 0
                #   ● Negative QUERY embeddings are considered class 1
                #
                # Different from the document, we are going to switch the classes
                # so that the positive class is 1 and the negative class is 0.

                # We want to group the masked tokens from the support set with
                # the positive tokens from the query set. Both of these
                # embeddings are from the same class, they represent dataset
                # tokens.
                class_1_embedding = torch.concat([mask_embedding, label_embedding], dim=0).mean(dim=0, keepdim=True) # [1, emb_dim]


                # We want to group the non-masked tokens from the support set
                # with the negative tokens from the query set. Both of these
                # embeddings represent non-dataset tokens.
                class_0_embedding = torch.concat([non_mask_embedding, non_label_embedding], dim=0).mean(dim=0, keepdim=True) # [1, emb_dim]


                # We want to group the [cls] tokens into their respective classes
                class_1_cls_support_embedding = support_embedding[support_labels == 1].mean(dim=0)  # [emb_dim]
                class_0_cls_support_embedding = support_embedding[support_labels == 0].mean(dim=0)  # [emb_dim]

                class_1_cls_query_embedding = label_embedding[query_labels == 1].mean(dim=0)  # [emb_dim]
                class_0_cls_query_embedding = non_label_embedding[query_labels == 0].mean(dim=0)  # [emb_dim]

                class_1_cls_embedding = torch.concat(
                    [class_1_cls_support_embedding, class_1_cls_query_embedding],
                    dim=0
                ).mean(dim=0, keepdim=True) # [1, emb_dim]
                class_0_cls_embedding = torch.concat(
                    [class_0_cls_support_embedding, class_0_cls_query_embedding],
                    dim=0
                ).mean(dim=0, keepdim=True) # [1, emb_dim]

                class_1_samples = torch.concat(
                    [class_1_embedding, class_1_cls_embedding],
                    dim=0
                ) # [2, emb_dim]

                class_0_samples = torch.concat(
                    [class_0_embedding, class_0_cls_embedding],
                    dim=0
                ) # [2, emb_dim]


                metric_labels = torch.concat(
                    [
                        torch.ones(len(class_1_samples)),
                        torch.zeros(len(class_0_samples))
                    ],
                    dim=0
                ) # [4]


                # This is our metric based loss
                loss_m =metric_loss(
                    torch.concat([class_1_samples, class_0_samples], dim=0),
                    metric_labels
                )


                # Now we compute the token classification loss for the query set

                # TODO: continue here with token classification



                metric_optimizer.step()
                optimizer.step()




if __name__ == "__main__":
    bm.train = train
    bm.validate = validate
    bm.main()