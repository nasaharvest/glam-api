# seperate queue function file to avoid circular model imports in post save methods

import os
import datetime
import logging
from tqdm import tqdm

from django.conf import settings


# def update_baseline_hook(task):
#     from django_q.tasks import async_task

#     if task.success:
#         async_task(
#             'server.utils.ingest.update_baselines_by_date',
#             task.args[0], task.args[1])


# def queue_baseline_update(product, date):
#     from django_q.tasks import async_task

#     from glam_data_processing.baselines import updateBaselines

#     # get optimal processing parameters
#     if product.meta['optimal_bsf']:
#         bsf = product.meta['optimal_bsf']
#     else:
#         bsf = settings.BLOCK_SCALE_FACTOR

#     if product.meta['optimal_cores']:
#         if product.meta['optimal_cores'] > settings.N_PROCESSES:
#             n_cores = settings.N_PROCESSES
#         else:
#             n_cores = product.meta['optimal_cores']
#     else:
#         n_cores = settings.N_PROCESSES

#     date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')

#     async_task(
#         updateBaselines, product.name,
#         date_obj, n_cores, bsf, hook=update_baseline_hook)


# def queue_dataset_stats_queue(product_id: str, date: str):
#     from django_q.tasks import async_task
#     async_task(
#         'glam.utils.stats.queue_dataset_stats',
#         product_id, date)
