from datasets import get_dataset_config_names, load_dataset

# all_categories = get_dataset_config_names("McAuley-Lab/Amazon-Reviews-2023", trust_remote_code=True)
# print(all_categories)

datasets = load_dataset("McAuley-Lab/Amazon-Reviews-2023", "raw_meta_All_Beauty", split="full", trust_remote_code=True)

for i in range(10):
    print(datasets[i])
