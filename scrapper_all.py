import requests
from bs4 import BeautifulSoup
from finalMapping_v2 import is_it_a_nationality
from finalMapping_v2 import is_arabic_country
from finalWordCloud import generate_word_cloud
from graphs import generate_graphs, generate_interactive_graph
from gliner import GLiNER
import re
import csv
from collections import Counter
import os

# Initialize GLiNER with the base model
model = GLiNER.from_pretrained("urchade/gliner_multi-v2.1")

pronoun_list = {"he", "she", "him", "her", "it", "they", "them", "we", "us", "i", "me", "you", "his", "their", "our"}

labels = ["Human", "Country", "Date", "Era", "Material"]
labels2 = ["مادة", "عصر", "تاريخ", "دولة", "إنسان"]
labels3 = ["Person", "Place", "City", "Country", "Date"]
labels4 = ["مدينة", "مكان", "تاريخ", "دولة", "اسم"]

# Function to extract content between start and end phrases
def fetch_main_content_advanced(url, start_phrase, end_phrase):
    response = requests.get(url)
    if response.status_code == 200:
        content = response.text
        soup = BeautifulSoup(content, "html.parser")
        clean_content = re.sub(r'<[^>]+>', ' ', str(soup))
        # Find content between the specified phrases
        start_index = clean_content.find(start_phrase)
        end_index = clean_content.find(end_phrase, start_index)

        if start_index != -1 and end_index != -1:
            extracted_content = clean_content[start_index:end_index].strip()
            return split_into_chunks(extracted_content)
        else:
            raise ValueError("Specified phrases not found in the content.")
    else:
        raise Exception(f"Failed to fetch {url}, status code: {response.status_code}")

# Function to split content into word-safe chunks
def split_into_chunks(content, chunk_size=500):
    words = content.split()
    chunks = []
    current_chunk = []

    for word in words:
        if len(" ".join(current_chunk + [word])) > chunk_size:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
        else:
            current_chunk.append(word)

    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return chunks

# Function to extract entities from content 
def extract_entities(biography_content, bio_url, website_type, language):
    all_entities = []
    print(f"\nextracting entities for: {bio_url}")

    if website_type == 2:
        if "/en/" in bio_url.lower():
            #print("Language: English")
            #language = "English"
            current_labels = labels3  # labels for website_type 2 and /en/ in URL
            threshold = 0.5
        elif "/ar/" in bio_url.lower():
           # print("Language: Arabic")
            #language = "Arabic"
            current_labels = labels4  # labels for website_type 2 and /ar/ in URL
            threshold = 0.6

    elif website_type == 1:
        if "/en/" in bio_url.lower():
            #print("Language: English")
            #language = "English"
            current_labels = labels  # labels for website_type 1 and /en/ in URL
            threshold = 0.5
        elif "/ar/" in bio_url.lower():
            #print("Language: Arabic")
            #language = "Arabic"
            current_labels = labels2  # labels for website_type 1 and /ar/ in URL
            threshold = 0.6

    else:
        raise ValueError("Language not recognized. URL must contain '/en/' or '/ar/'.")

    for chunk in biography_content:
        entities = model.predict_entities(chunk, current_labels, threshold)
        all_entities.extend(entities)

    arabic_pattern = re.compile(r'[\u0600-\u06FF]')
    human_names = set()
    countries = set()
    dates = set()
    places = set()
    cities = set()

    for entity in all_entities:
        label = entity["label"]
        text = entity["text"].strip()
        if website_type == 2 and language == "English":
            # Process entities for English
            if label == "Person" and text[0].isupper() and text.lower() not in pronoun_list:
                human_names.add((text, label))
            elif label == "Country":
                country = is_it_a_nationality('countries_and_demonyms.csv', text) or text
                countries.add((country, label))
            elif label == "Date":
                match = re.search(r'\b(18|19|20)\d{2}\b', text)
                if match:
                    dates.add((match.group(0), label))
            elif label == "Place":
                places.add((text, label))
            elif label == "City":
                cities.add((text, label))

        elif website_type == 2 and language == "Arabic":
            if label in ["اسم", "دولة", "مكان", "مدينة"] and not arabic_pattern.search(text):
                continue
            # Process entities for Arabic
            if label == "اسم":
                human_names.add((text, label))
            elif label == "دولة":
                countries.add((text, label))
            elif label == "تاريخ":
                match = re.search(r'\b(18|19|20)\d{2}\b', text)
                if match:
                    dates.add((match.group(0), label))
            elif label == "مكان":
                places.add((text, label))
            elif label == "مدينة":
                if not is_arabic_country('countries_and_demonyms.csv', text):
                    cities.add((text, label))

        if website_type == 1 and language == "English":
            # Process entities for English
            if label == "Human" and text[0].isupper() and text.lower() not in pronoun_list:
                human_names.add((text, label))
            elif label == "Country":
                country = is_it_a_nationality('countries_and_demonyms.csv', text) or text
                countries.add((country, label))
            elif label == "Date":
                match = re.search(r'\b(18|19|20)\d{2}\b', text)
                if match:
                    dates.add((match.group(0), label))
            elif label == "Era":
                places.add((text, label))
            elif label == "Material":
                cities.add((text, label))

        elif website_type == 1 and language == "Arabic":
            if label in ["مادة", "عصر", "تاريخ", "دولة", "إنسان"] and not arabic_pattern.search(text):
                continue
            # Process entities for Arabic
            if label == "إنسان":
                human_names.add((text, label))
            elif label == "دولة":
                countries.add((text, label))
            elif label == "تاريخ":
                match = re.search(r'\b(18|19|20)\d{2}\b', text)
                if match:
                    dates.add((match.group(0), label))
            elif label == "عصر":
                places.add((text, label))
            elif label == "مادة":
                if not is_arabic_country('countries_and_demonyms.csv', text):
                    cities.add((text, label))

   # print(f"Processing chunk with labels: {current_labels} and threshold: {threshold}")
    sorted_human_names = sorted(human_names, key=lambda x: x[0])
    sorted_countries = sorted(countries, key=lambda x: x[0])
    sorted_dates = sorted(dates, key=lambda x: int(x[0]) if x[0].isdigit() else x[0])
    sorted_places = sorted(places, key=lambda x: x[0])
    sorted_cities = sorted(cities, key=lambda x: x[0])

    return sorted_human_names, sorted_countries, sorted_dates, sorted_places, sorted_cities

# Function to process content and save results
def process_bio_page(bio_url, biography_content, folder_name, website_type):
    os.makedirs(folder_name, exist_ok=True)
    if website_type == 2:
        if "/en/" in bio_url.lower():
            language = "English"
        elif "/ar/" in bio_url.lower():
            language = "Arabic"
        else:
            raise ValueError("Language not recognized. URL must contain '/en/' or '/ar/'.")
    elif website_type == 1:
        if "/en/" in bio_url.lower():
            language = "English"
        elif "/ar/" in bio_url.lower():
            language = "Arabic"
        else:
            raise ValueError("Language not recognized. URL must contain '/en/' or '/ar/'.")
    else:
        raise ValueError("Invalid website_type provided. Must be 1 or 2.")


    human_names, countries, dates, places, cities = extract_entities(biography_content, bio_url, website_type, language)

    entity_label_counts = Counter()
    all_entities_set = set(human_names).union(set(countries), set(dates), set(places), set(cities))

    for entity_tuple in all_entities_set:
        entity = entity_tuple[0]
        count = sum(chunk.count(entity) for chunk in biography_content)
        label = entity_tuple[1]
        entity_label_counts[(entity, label)] = count

    sorted_entity_counts = sorted(entity_label_counts.items(), key=lambda x: x[0])

    csv_name = os.path.join(folder_name, bio_url.split('/')[-1].replace('.aspx', '') + '.csv')

    with open(csv_name, mode='w', newline='', encoding='utf-8-sig') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(['Link', 'Entity', 'Label', 'Occurrences'])
        for (entity, label), count in sorted_entity_counts:
            writer.writerow([bio_url, entity, label, count])

    print(f"\nEntities saved to {csv_name}")

    word_cloud_image = generate_word_cloud(csv_name, [bio_url], os.path.join(folder_name, bio_url.split('/')[-1].replace('.aspx', '') + '_wordcloud.png'))
    graph_image = generate_graphs(csv_name)
   # if language == "English":
        #interactive_graph = generate_interactive_graph(csv_name)

    with open("all_entities.csv", mode='a', newline='', encoding='utf-8-sig') as csv_file:
        writer = csv.writer(csv_file)
        for (entity, label), count in sorted_entity_counts:
            writer.writerow([bio_url, entity, label, count])

