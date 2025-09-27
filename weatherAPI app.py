import sys
import requests
import json
from dotenv import load_dotenv
import os


from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QComboBox, QCompleter, QMessageBox
)
from PyQt5.QtCore import Qt, QStringListModel

import pycountry
import geonamescache

load_dotenv()

class WeatherApp(QWidget):


    def __init__(self):
        super().__init__()

        self.country_label = QLabel("Pick A Country:", self)
        self.country_combo = QComboBox(self)
        self.find_location_btn = QPushButton("📍 Find My Location", self)
        self.city_label = QLabel("Pick A City", self)
        self.city_combo = QComboBox(self)

        self.get_weather_btn = QPushButton("Get Weather", self)
        self.temprature_label = QLabel(self)
        self.description_label = QLabel(self)

        #for country and city data 
        self.gc = geonamescache.GeonamesCache()
        self.cities = self.gc.get_cities() 

        #preparing for listing countries and cities 
        self.country_list = self.build_country_list()
        self._prepare_city_completer()  # Önce city completer'ı hazırla
        self._populate_countries()      # Sonra ülkeleri doldur
        self.initUI()

    def build_country_list(self):
        items = []
        
        for country in pycountry.countries:
            name = getattr(country, "name", "").replace("Republic of ", "").replace("State of ", "")
            alpha2 = getattr(country, "alpha_2", "")

            if not alpha2 or not name:
                continue

            # Emoji'siz sadece isim ve kod
            display = f"{name} ({alpha2})"
            items.append((alpha2, display))

        items.sort(key=lambda x: x[1])
        return items 

    def _populate_countries(self):
        self.country_combo.clear()

        for alpha2, display in self.country_list:
            self.country_combo.addItem(display, alpha2)

        # Türkiye'yi varsayılan olarak seç
        for i in range(self.country_combo.count()):
            if self.country_combo.itemData(i) == "TR":
                self.country_combo.setCurrentIndex(i)
                break
        
        # Ülke değiştiğinde şehirleri güncelle
        self.country_combo.currentIndexChanged.connect(self._on_country_changed)

        # Ülke combo'sunu aranabilir yap - ama farklı yöntemle
        self.country_combo.setEditable(True)
        self.country_combo.setInsertPolicy(QComboBox.NoInsert)
        self.country_combo.setDuplicatesEnabled(False)
        
        # Ülke için completer - emoji'siz daha iyi çalışır
        country_names = [self.country_combo.itemText(i) for i in range(self.country_combo.count())]
        self.country_completer = QCompleter(country_names, self)
        self.country_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.country_completer.setFilterMode(Qt.MatchContains)  # Bu özelliği geri ekledim
        self.country_completer.setCompletionMode(QCompleter.PopupCompletion)
        self.country_combo.setCompleter(self.country_completer)
        
        # Farklı bir yaklaşım - line edit'e erişim
        line_edit = self.country_combo.lineEdit()
        if line_edit:
            line_edit.setReadOnly(False)

        # İlk yükleme için şehirleri güncelle
        self._on_country_changed()

    #city completer for countries 
    def _on_country_changed(self):
        alpha2 = self.country_combo.currentData()
        if not alpha2:
            print("No country selected")
            return

        print(f"Selected country: {alpha2}")

        # Önce tüm şehirleri görelim
        all_cities_for_country = []
        for c in self.cities.values():
            if c.get("countrycode", "").upper() == alpha2.upper():
                all_cities_for_country.append(c)
        
        print(f"Total cities for {alpha2}: {len(all_cities_for_country)}")
        
        # İlk 5 şehri örnek olarak göster
        for i, city in enumerate(all_cities_for_country[:5]):
            print(f"  {i+1}. {city.get('name', 'N/A')} - {city.get('feature_code', 'N/A')} - Pop: {city.get('population', 0)}")

        # Basit filtreleme - sadece nüfusa göre
        if alpha2.upper() == "TR":
            # Türkiye için nüfusu 50,000'den fazla olanlar
            filtered = [c for c in all_cities_for_country if c.get("population", 0) > 50000]
        else:
            # Diğer ülkeler için nüfusu 20,000'den fazla olanlar
            filtered = [c for c in all_cities_for_country if c.get("population", 0) > 20000]
        
        print(f"Filtered cities: {len(filtered)}")

        # ÖNEMLİ DEĞİŞİKLİK: Sadece alfabetik sıralama yap, nüfus sıralaması kaldırıldı
        filtered.sort(key=lambda x: x.get("name", ""))

        # Şehir listesini oluştur
        seen = set()
        city_items = []
        for city in filtered:
            name = city.get("name", "").strip()
            if name and name not in seen:
                seen.add(name)
                city_items.append((name, name))

        # Şehir combo'sunu güncelle
        self.city_combo.clear()

        if not city_items:
            self.city_combo.addItem("No cities found", userData=None)
            self.city_combo.setEnabled(False)
        else:
            self.city_combo.setEnabled(True)
            # ÖNEMLİ: İlk şehri otomatik seçme, boş bırak
            self.city_combo.addItem("Select a city...", userData=None)
            for name, disp in city_items:
                self.city_combo.addItem(disp, userData=name)

        # Şehir completer'ını güncelle
        city_names_display = [self.city_combo.itemText(i) for i in range(1, self.city_combo.count())]  # İlk item'i atla
        self.city_completer_model.setStringList(city_names_display)

    def _prepare_city_completer(self):
        self.city_combo.setEditable(True)
        self.city_combo.setInsertPolicy(QComboBox.NoInsert)
        self.city_combo.setDuplicatesEnabled(False)
        
        self.city_completer_model = QStringListModel([])
        self.city_completer = QCompleter(self.city_completer_model, self)
        self.city_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.city_completer.setFilterMode(Qt.MatchContains)  # Bu özelliği geri ekledim
        self.city_completer.setCompletionMode(QCompleter.PopupCompletion)
        self.city_combo.setCompleter(self.city_completer)
        
        line_edit = self.city_combo.lineEdit()
        if line_edit:
            line_edit.setReadOnly(False)

    def initUI(self):
        self.setWindowTitle("Weather App")

        vbox = QVBoxLayout()
        vbox.addWidget(self.country_label)
        vbox.addWidget(self.country_combo)
        vbox.addWidget(self.find_location_btn)
        vbox.addWidget(self.city_label)
        vbox.addWidget(self.city_combo)
        vbox.addWidget(self.get_weather_btn)
        vbox.addWidget(self.temprature_label)
        vbox.addWidget(self.description_label)

        self.setLayout(vbox)

        # Hizalamalar
        for w in (self.country_label, self.city_label,
                  self.temprature_label, self.description_label):
            w.setAlignment(Qt.AlignCenter)

        # ObjectName'ler (stil için)
        self.country_label.setObjectName("country_label")
        self.city_label.setObjectName("city_label")
        self.temprature_label.setObjectName("temprature_label")
        self.description_label.setObjectName("description_label")
        self.get_weather_btn.setObjectName("get_weather_btn")
        self.find_location_btn.setObjectName("find_location_btn")

        # Stil
        self.setStyleSheet("""
            QLabel, QPushButton, QComboBox {
                font-family: Arial;
            }
            QLabel#country_label, QLabel#city_label {
                font-size: 32px;
                font-style: italic;
            }
            QComboBox {
                font-size: 26px;
                padding: 8px 10px;
            }
            QComboBox QAbstractItemView {
                font-size: 22px;
            }
            QPushButton#get_weather_btn {
                font-size: 28px;
                font-weight: bold;
                padding: 8px 12px;
            }
            QPushButton#find_location_btn {
                font-size: 20px;
                font-weight: bold;
                padding: 6px 10px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton#find_location_btn:hover {
                background-color: #45a049;
            }
            QLabel#temprature_label {
                font-size: 75px;
            }
            QLabel#description_label {
                font-size: 48px;
            }
        """)

        # Click events
        self.get_weather_btn.clicked.connect(self.get_weather)
        self.find_location_btn.clicked.connect(self.find_my_location)

    def find_my_location(self):
        """IP-based location detection and automatic country/city selection"""
        # Show loading state
        original_text = self.find_location_btn.text()
        self.find_location_btn.setText("🔍 Finding location...")
        self.find_location_btn.setEnabled(False)
        
        # Show temporary message
        self.temprature_label.setStyleSheet("font-size: 25px; color: blue;")
        self.temprature_label.setText("Detecting location...")
        self.description_label.setText("")
        
        try:
            # Try multiple IP location services and get consensus
            location_results = []
            services = [
                ("http://ipapi.co/json/", "ipapi"),
                ("http://ip-api.com/json/", "ip-api"),
                ("https://ipinfo.io/json", "ipinfo")
            ]
            
            for service_url, service_name in services:
                try:
                    print(f"Trying service: {service_name}")
                    response = requests.get(service_url, timeout=8)
                    response.raise_for_status()
                    data = response.json()
                    print(f"Response from {service_name}: {data}")
                    
                    # Normalize data from different services
                    if service_name == "ipapi":
                        country_code = data.get("country_code", "").upper()
                        country_name = data.get("country_name", "")
                        city = data.get("city", "")
                        region = data.get("region", "")
                    elif service_name == "ip-api":
                        country_code = data.get("countryCode", "").upper()
                        country_name = data.get("country", "")
                        city = data.get("city", "")
                        region = data.get("regionName", "")
                    elif service_name == "ipinfo":
                        country_code = data.get("country", "").upper()
                        country_name = country_code  # ipinfo doesn't give full name
                        city = data.get("city", "")
                        region = data.get("region", "")
                    
                    if country_code and (city or region):
                        location_results.append({
                            'service': service_name,
                            'country_code': country_code,
                            'country_name': country_name,
                            'city': city,
                            'region': region
                        })
                        print(f"{service_name} says: {country_name} ({country_code}), {city}, {region}")
                        
                except Exception as e:
                    print(f"Service {service_name} failed: {e}")
                    continue
            
            if not location_results:
                self.display_error("Could not reach any location service.")
                return
            
            # Analyze results for consensus
            countries = [r['country_code'] for r in location_results]
            cities = [r['city'] for r in location_results if r['city']]
            regions = [r['region'] for r in location_results if r['region']]
            
            # Use most common country
            country_code = max(set(countries), key=countries.count) if countries else None
            country_name = next((r['country_name'] for r in location_results if r['country_code'] == country_code), "")
            
            # For city, show multiple options if they differ
            all_locations = list(set(cities + regions))
            if len(all_locations) == 1:
                # All services agree
                detected_city = all_locations[0]
                confidence = "high"
            elif len(all_locations) > 1:
                # Services disagree - ALWAYS PREFER REGIONS over cities
                if regions:
                    # Count occurrences in regions
                    region_counts = {}
                    for r in regions:
                        region_counts[r] = region_counts.get(r, 0) + 1
                    detected_city = max(region_counts, key=region_counts.get)
                    confidence = "medium"

                else:
                    # Fallback to cities if no regions
                    city_counts = {}
                    for c in cities:
                        city_counts[c] = city_counts.get(c, 0) + 1
                    detected_city = max(city_counts, key=city_counts.get)
                    confidence = "low"

            else:
                detected_city = None
                confidence = "none"
            
            if not country_code:
                self.display_error("Country information could not be retrieved.")
                return
                
            # Find and select country in combo
            country_found = False
            for i in range(self.country_combo.count()):
                item_data = self.country_combo.itemData(i)
                if item_data and item_data.upper() == country_code:
                    self.country_combo.setCurrentIndex(i)
                    country_found = True
                    print(f"Country selected: {self.country_combo.currentText()}")
                    break
            
            if not country_found:
                self.display_error(f"Country ({country_code}) not found in the list.")
                return
            
            # If city info exists, find and select city
            if detected_city and confidence in ["high", "medium", "low"]:
                # Wait for cities to load
                self._on_country_changed()  # Update cities
                
                # Try to find and select the detected city
                city_found = False
                city_variations = []
                
                # Add primary detected city
                if detected_city:
                    city_variations.extend([
                        detected_city,
                        detected_city.replace("ı", "i").replace("İ", "I"),
                        detected_city.replace("i", "ı").replace("I", "İ"),
                        detected_city.lower(),
                        detected_city.upper(),
                        detected_city.title(),
                    ])
                    
                    # SMART DISTRICT TO CITY MAPPING for Turkey
                    if country_code == "TR":
                        district_to_city = {
                            'etimesgut': 'Ankara',
                            'çankaya': 'Ankara', 
                            'keçiören': 'Ankara',
                            'mamak': 'Ankara',
                            'sincan': 'Ankara',
                            'altındağ': 'Ankara',
                            'yenimahalle': 'Ankara',
                            'gölbaşı': 'Ankara',
                            'pursaklar': 'Ankara',
                            'elvankent': 'Ankara',
                            'beşiktaş': 'Istanbul',
                            'kadıköy': 'Istanbul',
                            'üsküdar': 'Istanbul',
                            'şişli': 'Istanbul',
                            'beyoğlu': 'Istanbul',
                            'fatih': 'Istanbul',
                            'bakırköy': 'Istanbul',
                            'zeytinburnu': 'Istanbul',
                            'kartal': 'Istanbul',
                            'maltepe': 'Istanbul',
                            'ataşehir': 'Istanbul',
                            'pendik': 'Istanbul',
                            'tuzla': 'Istanbul',
                            'seyhan': 'Adana',
                            'yüreğir': 'Adana',
                            'çukurova': 'Adana',
                            'sarıçam': 'Adana',
                            'konak': 'Izmir',
                            'bornova': 'Izmir',
                            'karşıyaka': 'Izmir',
                            'buca': 'Izmir',
                            'alsancak': 'Izmir',
                        }
                        
                        detected_lower = detected_city.lower().replace("i", "ı").replace("İ", "I")
                        if detected_lower in district_to_city:
                            main_city = district_to_city[detected_lower]
                            city_variations.insert(0, main_city)  # Add at beginning (priority)
                            city_variations.extend([
                                main_city.lower(),
                                main_city.upper(),
                                main_city.replace("ı", "i").replace("İ", "I"),
                            ])
                
                # Add other detected locations as alternatives (REGIONS FIRST!)
                regions_first = [loc for loc in all_locations if loc in regions]
                cities_after = [loc for loc in all_locations if loc not in regions and loc != detected_city]
                
                for loc in regions_first + cities_after:
                    if loc and loc != detected_city:
                        city_variations.extend([
                            loc,
                            loc.replace("ı", "i").replace("İ", "I"),
                            loc.replace("i", "ı").replace("I", "İ"),
                            loc.lower(),
                            loc.upper(),
                        ])
                
                # Remove duplicates
                seen = set()
                unique_variations = []
                for var in city_variations:
                    if var and var not in seen:
                        seen.add(var)
                        unique_variations.append(var)
                
                print(f"Trying city variations: {unique_variations}")
                
                for variation in unique_variations:
                    if not variation:
                        continue
                        
                    for i in range(1, self.city_combo.count()):
                        combo_city = self.city_combo.itemText(i)
                        combo_city_lower = combo_city.lower()
                        variation_lower = variation.lower()
                        
                        print(f"  Comparing '{variation}' with '{combo_city}'")
                        
                        # Try exact match first
                        if variation_lower == combo_city_lower:
                            self.city_combo.setCurrentIndex(i)
                            city_found = True
                            break
                        
                        # Then try partial match
                        elif variation_lower in combo_city_lower or combo_city_lower in variation_lower:
                            if len(variation) >= 3 and len(combo_city) >= 3:
                                self.city_combo.setCurrentIndex(i)
                                city_found = True
                                break
                    
                    if city_found:
                        break
                
                if city_found:
                    selected_city = self.city_combo.currentText()
                    self.temprature_label.setStyleSheet("font-size: 25px; color: green;")
                    self.temprature_label.setText(f"📍 Location found!")
                    self.description_label.setText(f"{country_name}, {selected_city}")
                    
                    # Optional: Show what was detected vs what was selected (for info only)
                    if detected_city.lower() != selected_city.lower():
                        print(f"ℹ️ NOTE: Detected '{detected_city}' but selected '{selected_city}' (smart mapping)")
                    else:
                        print(f"ℹ️ NOTE: Perfect match - detected and selected: '{selected_city}'")
                else:
                    self.temprature_label.setStyleSheet("font-size: 20px; color: orange;")
                    self.temprature_label.setText(f"📍 Country found, please select city manually")
                    if len(all_locations) > 1:
                        self.description_label.setText(f"{country_name} - Multiple locations detected: {', '.join(all_locations[:3])}")
                    else:
                        self.description_label.setText(f"{country_name} - Detected: {detected_city} (not found in list)")
                    
                    # Show available cities for debugging
                    available_cities = []
                    for i in range(1, min(6, self.city_combo.count())):
                        available_cities.append(self.city_combo.itemText(i))
                    print(f"Available cities: {available_cities}")
                    
            else:
                self.temprature_label.setStyleSheet("font-size: 25px; color: orange;")
                self.temprature_label.setText(f"📍 Country found!")
                self.description_label.setText(f"{country_name} - City information not available")
                
        except requests.exceptions.RequestException as e:
            print(f"Network error: {e}")
            self.display_error("Internet connection error. Location could not be detected.")
            
        except Exception as e:
            print(f"Location error: {e}")
            self.display_error("An error occurred while detecting location.")
            
        finally:
            # Restore button to original state
            self.find_location_btn.setText(original_text)
            self.find_location_btn.setEnabled(True)

    def get_weather(self):
        api_key = os.getenv("WEATHER_API_KEY")
    
        alpha2 = self.country_combo.currentData()
        city_name = self.city_combo.currentData()

        if not alpha2 or not city_name:
            self.display_error("Please select country and city.")
            return

        # OpenWeather için "City,CC" formatı
        query = f"{city_name},{alpha2}"
        base_url = f"http://api.openweathermap.org/data/2.5/weather?q={query}&appid={api_key}&lang=tr"

        try:
            response = requests.get(base_url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if str(data.get("cod")) == "200":
                self.display_weather(data)
            else:
                self.display_error(data.get("message", "Unknown error"))

        except requests.exceptions.HTTPError:
            status = getattr(response, "status_code", None)
            if status == 401:
                self.display_error("Invalid API key.")
            elif status == 404:
                self.display_error("City not found.")
            elif status == 403:
                self.display_error("Access denied.")
            else:
                self.display_error("HTTP error occurred.")
        except requests.exceptions.RequestException:
            self.display_error("Network error occurred.")

    def display_error(self, message):
        self.temprature_label.setStyleSheet("font-size: 30px; color: red;")
        self.temprature_label.setText(message)
        self.description_label.setText("")

    def display_weather(self, data):
        # Kelvin -> °C
        celcius_temp = int(round(data["main"]["temp"] - 273.15))
        weather_id = data["weather"][0]["id"]
        weather_description = data["weather"][0]["description"]

        emoji = self.get_weather_emoji(weather_id)

        self.temprature_label.setStyleSheet("font-size: 75px; color: black;")
        self.temprature_label.setText(f"{celcius_temp}°C {emoji}")
        self.description_label.setText(weather_description.capitalize())

    @staticmethod
    def get_weather_emoji(weather_id):
        if 200 <= weather_id <= 232:
            return "⛈️"
        elif 300 <= weather_id <= 321:
            return "🌦️"
        elif 500 <= weather_id <= 531:
            return "🌧️"
        elif 600 <= weather_id <= 622:
            return "❄️"
        elif 701 <= weather_id <= 741:
            return "🌫️"
        elif weather_id == 762:
            return "🌋"
        elif weather_id == 771:
            return "💨"
        elif weather_id == 781:
            return "🌪️"
        elif weather_id == 800:
            return "☀️"
        elif 801 <= weather_id <= 804:
            return "☁️"
        else:
            return "🌍"


if __name__ == "__main__":
    app = QApplication(sys.argv)
    weather_app = WeatherApp()
    weather_app.show()
    sys.exit(app.exec_())