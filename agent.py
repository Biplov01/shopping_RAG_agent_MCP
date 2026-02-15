import os
import json
import sqlite3
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
from langchain_community.llms import Ollama
from langchain.agents import Tool, AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.agents import AgentType
from langchain.schema import SystemMessage
import re
import time

# ======================
# 1. PRODUCTS DATABASE (ENHANCED)
# ======================
class ProductDatabase:
    def __init__(self, db_path: str = "products.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Create and populate the products database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            price REAL NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            rating REAL DEFAULT 0,
            stock INTEGER DEFAULT 0,
            brand TEXT,
            thumbnail TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CHECK (price >= 0),
            CHECK (rating >= 0 AND rating <= 5)
        )
        ''')
        
        # Create user interaction log
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            response TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_category ON products(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_price ON products(price)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rating ON products(rating)')
        
        cursor.execute("SELECT COUNT(*) FROM products")
        count = cursor.fetchone()[0]
        
        if count == 0:
            print("📦 Loading sample products...")
            self._add_sample_products()
        
        conn.commit()
        conn.close()
    
    def _add_sample_products(self):
        """Add diverse sample products"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        sample_products = [
            # Electronics
            (1, "iPhone 15 Pro", 1199.99, "Electronics", "Latest iPhone with A17 Pro chip", 4.8, 45, "Apple", "iphone.jpg"),
            (2, "Samsung Galaxy S24", 899.99, "Electronics", "Android flagship phone", 4.7, 60, "Samsung", "galaxy.jpg"),
            (3, "MacBook Pro M3", 2499.99, "Computers", "16-inch laptop for professionals", 4.9, 25, "Apple", "macbook.jpg"),
            (4, "Dell XPS 15", 1799.99, "Computers", "Premium Windows laptop", 4.6, 35, "Dell", "xps.jpg"),
            (5, "Sony WH-1000XM5", 349.99, "Audio", "Noise cancelling headphones", 4.8, 80, "Sony", "headphones.jpg"),
            (6, "Bose Soundbar", 799.99, "Home Theater", "Premium sound system", 4.5, 40, "Bose", "soundbar.jpg"),
            
            # Fashion
            (7, "Nike Air Max", 149.99, "Footwear", "Running shoes", 4.4, 120, "Nike", "nike.jpg"),
            (8, "Adidas Ultraboost", 179.99, "Footwear", "Comfort running shoes", 4.6, 90, "Adidas", "adidas.jpg"),
            (9, "Levi's Jeans", 89.99, "Clothing", "Classic denim jeans", 4.3, 200, "Levi's", "jeans.jpg"),
            (10, "Rolex Submariner", 9999.99, "Watches", "Luxury diving watch", 4.9, 5, "Rolex", "rolex.jpg"),
            
            # Home & Kitchen
            (11, "Dyson V15", 749.99, "Home Appliances", "Cordless vacuum cleaner", 4.7, 50, "Dyson", "dyson.jpg"),
            (12, "Ninja Air Fryer", 129.99, "Kitchen", "Multi-cooker air fryer", 4.5, 150, "Ninja", "airfryer.jpg"),
            (13, "Nespresso Vertuo", 199.99, "Kitchen", "Coffee machine", 4.4, 75, "Nespresso", "nespresso.jpg"),
            
            # Gaming
            (14, "PlayStation 5", 499.99, "Gaming", "Gaming console", 4.8, 30, "Sony", "ps5.jpg"),
            (15, "Xbox Series X", 499.99, "Gaming", "4K gaming console", 4.7, 40, "Microsoft", "xbox.jpg"),
            (16, "Nintendo Switch", 299.99, "Gaming", "Hybrid gaming console", 4.6, 60, "Nintendo", "switch.jpg"),
            
            # Additional products for variety
            (17, "iPad Pro 12.9", 1099.99, "Electronics", "Professional tablet", 4.7, 55, "Apple", "ipad.jpg"),
            (18, "LG OLED TV", 1499.99, "Home Theater", "4K OLED Smart TV", 4.8, 20, "LG", "tv.jpg"),
            (19, "Instant Pot", 89.99, "Kitchen", "Pressure cooker", 4.5, 180, "Instant Pot", "instantpot.jpg"),
            (20, "GoPro Hero 12", 399.99, "Electronics", "Action camera", 4.6, 70, "GoPro", "gopro.jpg"),
        ]
        
        for product in sample_products:
            cursor.execute('''
            INSERT OR REPLACE INTO products 
            (id, title, price, category, description, rating, stock, brand, thumbnail)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', product)
        
        conn.commit()
        conn.close()
        print(f"✅ Loaded {len(sample_products)} diverse products")
    
    def execute_sql(self, sql: str) -> str:
        """Execute SQL and return formatted results"""
        try:
            # Basic SQL injection prevention - only allow SELECT queries for safety
            sql_upper = sql.strip().upper()
            if not sql_upper.startswith("SELECT"):
                return "❌ Only SELECT queries are allowed for safety."
            
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            cursor = conn.cursor()
            
            cursor.execute(sql)
            
            if sql_upper.startswith("SELECT"):
                results = cursor.fetchall()
                
                if not results:
                    conn.close()
                    return "No results found."
                
                # Convert to list of dictionaries
                formatted = []
                for row in results[:15]:  # Limit to 15 rows
                    row_dict = dict(row)
                    formatted.append(row_dict)
                
                conn.close()
                return json.dumps(formatted, indent=2, ensure_ascii=False)
            else:
                conn.commit()
                conn.close()
                return f"✅ Operation successful. {cursor.rowcount} rows affected."
                
        except sqlite3.Error as e:
            return f"❌ Database error: {str(e)}"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def log_query(self, user_query: str, response: str):
        """Log user interactions for learning"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO user_queries (query, response) VALUES (?, ?)",
                (user_query[:500], response[:2000])
            )
            conn.commit()
            conn.close()
        except Exception as e:
            # Don't crash if logging fails
            print(f"⚠️ Failed to log query: {e}")

# ======================
# 2. ENHANCED WEATHER SERVICE
# ======================
class WeatherService:
    def __init__(self):
        self.cache = {}
        self.cache_duration = 300  # 5 minutes cache
    
    def get_weather(self, location: str) -> str:
        """Get weather with better formatting"""
        try:
            # Clean location input
            location = location.strip().lower().replace(" ", "+")
            
            # Check cache
            current_time = time.time()
            if location in self.cache:
                cached_time, cached_data = self.cache[location]
                if current_time - cached_time < self.cache_duration:
                    return cached_data
            
            # Try wttr.in API
            try:
                url = f"https://wttr.in/{location}?format=j1"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (compatible; ShoppingAssistant/1.0)'
                }
                response = requests.get(url, timeout=10, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'current_condition' not in data:
                        raise ValueError("Invalid weather data format")
                    
                    current = data['current_condition'][0]
                    area = data['nearest_area'][0]['areaName'][0]['value']
                    
                    temp_c = current['temp_C']
                    temp_f = current['temp_F']
                    desc = current['weatherDesc'][0]['value']
                    humidity = current['humidity']
                    wind_kph = current['windspeedKmph']
                    wind_mph = current['windspeedMiles']
                    
                    # Determine weather advice
                    temp_int = int(temp_c)
                    if temp_int > 30:
                        advice = "🔥 Very hot! Stay hydrated, wear light clothes. Good for summer products."
                    elif temp_int > 25:
                        advice = "☀️ Warm. Perfect for outdoor activities. Consider sunglasses, hats."
                    elif temp_int > 18:
                        advice = "😊 Pleasant. Light clothing recommended."
                    elif temp_int > 10:
                        advice = "🌤️ Mild. A light jacket should be enough."
                    elif temp_int > 0:
                        advice = "🥶 Chilly. Wear a warm jacket, consider indoor products."
                    elif temp_int > -10:
                        advice = "❄️ Cold! Bundle up with winter wear, heaters recommended."
                    else:
                        advice = "🥶 Freezing! Heavy winter gear essential."
                    
                    result = f"""🌤️ **Weather in {area.title()}**
• Temperature: {temp_c}°C ({temp_f}°F)
• Condition: {desc}
• Humidity: {humidity}%
• Wind: {wind_kph} km/h ({wind_mph} mph)

👕 **Shopping Recommendation:** {advice}""".strip()
                    
                    # Cache the result
                    self.cache[location] = (current_time, result)
                    
                    return result
                    
            except Exception as api_error:
                print(f"Weather API error: {api_error}")
            
            # Fallback to simple format
            url = f"https://wttr.in/{location}?format=3"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                result = f"🌤️ Weather: {response.text.strip()}"
                self.cache[location] = (current_time, result)
                return result
            
            result = f"🌤️ Weather data for '{location.replace('+', ' ').title()}' not available. Try another city."
            self.cache[location] = (current_time, result)
            return result
                
        except requests.RequestException as e:
            return f"❌ Weather service error: Could not connect to weather service."
        except Exception as e:
            return f"❌ Weather service error: {str(e)[:100]}"

# ======================
# 3. FIXED SHOPPING AGENT
# ======================
class SmartShoppingAgent:
    def __init__(self, model_name: str = "llama3.1:8b"):
        """
        Initialize the shopping agent.
        
        Args:
            model_name: Name of the Ollama model to use
        """
        # Initialize services
        self.db = ProductDatabase()
        self.weather = WeatherService()
        
        # Initialize Ollama with FIXED settings
        self.llm = Ollama(
            model=model_name,
            base_url="http://localhost:11434",
            temperature=0.2,  # Lower temperature for more consistent responses
            # Removed num_predict as it's not a valid parameter for LangChain Ollama
        )
        
        # Create enhanced tools
        self.tools = [
            Tool(
                name="ProductDatabase",
                func=self._query_database,
                description="""Use this tool to search for products. Input must be a valid SQL SELECT query.
                Available columns: id, title, price, category, description, rating, stock, brand, thumbnail.
                Categories include: Electronics, Computers, Audio, Home Theater, Footwear, Clothing, Watches, 
                Home Appliances, Kitchen, Gaming.
                Always use LIKE for text searches and ORDER BY for sorting.
                Example queries:
                - "SELECT * FROM products WHERE category LIKE '%electronics%' AND price < 1000 ORDER BY rating DESC LIMIT 5"
                - "SELECT title, price, rating FROM products WHERE brand LIKE '%apple%' ORDER BY price ASC LIMIT 10"
                - "SELECT * FROM products WHERE category = 'Gaming' AND price < 500 ORDER BY rating DESC"
                """
            ),
            Tool(
                name="WeatherService",
                func=self.weather.get_weather,
                description="""Use this tool to get weather information for shopping recommendations.
                Input: City name (e.g., 'New York', 'London', 'Tokyo', 'Paris').
                Returns: Weather conditions, temperature, and shopping recommendations.
                """
            ),
            Tool(
                name="ProductRecommendations",
                func=self._get_recommendations,
                description="""Get intelligent product recommendations based on context.
                Input must be valid JSON with optional fields:
                - budget: maximum price (e.g., 500)
                - category: product category (e.g., "electronics")
                - min_rating: minimum rating (e.g., 4.0)
                - weather: weather condition (e.g., "rainy", "sunny", "cold")
                Example: '{"budget": 1000, "category": "electronics", "min_rating": 4.5}'
                """
            )
        ]
        
        # Enhanced ReAct prompt template
        prompt_template = """You are an intelligent shopping assistant powered by advanced AI. Your purpose is to help users find products, get recommendations, and make informed purchasing decisions.

You have access to the following tools:

{tools}

To use a tool, you must follow this EXACT format:

Question: the user's question
Thought: think about what the user wants and which tool to use
Action: the action to take, must be one of [{tool_names}]
Action Input: the input to the action (must be correct format for the tool)
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat up to 3 times if needed)
Thought: I now have enough information to answer
Final Answer: the final, helpful answer to the user

IMPORTANT RULES:
1. If the user asks about products, use ProductDatabase tool with SQL queries
2. If the user mentions weather, use WeatherService tool
3. If the user asks for recommendations, use ProductRecommendations tool
4. Always be helpful, friendly, and provide detailed information
5. Format prices with $ and ratings with stars

Previous conversation history:
{chat_history}

Question: {input}
Thought: {agent_scratchpad}"""
        
        # Create the prompt
        self.prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["input", "chat_history", "agent_scratchpad", "tools", "tool_names"]
        )
        
        # Initialize memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="output"
        )
        
        # Create agent using create_react_agent
        try:
            self.agent = create_react_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=self.prompt
            )
        except Exception as e:
            # Fallback for LangChain version differences
            print(f"Note: Using alternative agent creation method. Error: {e}")
            from langchain import hub
            prompt = hub.pull("hwchase17/react")
            self.agent = create_react_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=prompt
            )
        
        # Create agent executor
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            max_iterations=5,
            handle_parsing_errors=True,
            return_intermediate_steps=False,
            early_stopping_method="generate"
        )
    
    def _query_database(self, sql_query: str) -> str:
        """Execute SQL query and log it"""
        # Validate SQL query for safety
        sql_upper = sql_query.strip().upper()
        if not sql_upper.startswith("SELECT"):
            return "Error: Only SELECT queries are allowed."
        
        # Add safety limits if not present
        if "LIMIT" not in sql_upper and "COUNT" not in sql_upper:
            sql_query = sql_query.rstrip(';') + " LIMIT 10;"
        
        result = self.db.execute_sql(sql_query)
        return result
    
    def _get_recommendations(self, criteria_json: str) -> str:
        """Generate product recommendations based on criteria"""
        try:
            criteria = json.loads(criteria_json)
            
            # Build SQL based on criteria
            conditions = []
            params = []
            
            if 'budget' in criteria:
                conditions.append("price <= ?")
                params.append(float(criteria['budget']))
            
            if 'category' in criteria:
                conditions.append("LOWER(category) LIKE LOWER(?)")
                params.append(f"%{criteria['category']}%")
            
            if 'min_rating' in criteria:
                conditions.append("rating >= ?")
                params.append(float(criteria['min_rating']))
            
            if 'brand' in criteria:
                conditions.append("LOWER(brand) LIKE LOWER(?)")
                params.append(f"%{criteria['brand']}%")
            
            # Weather-based recommendations
            if 'weather' in criteria:
                weather = criteria['weather'].lower()
                if weather in ['rainy', 'snow', 'cold', 'windy']:
                    conditions.append("category IN ('Home Appliances', 'Kitchen', 'Gaming', 'Audio', 'Home Theater')")
                elif weather in ['sunny', 'hot', 'warm', 'clear']:
                    conditions.append("category IN ('Footwear', 'Clothing', 'Electronics', 'Watches')")
            
            # Build final query
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            sql = f"""
            SELECT title, price, category, rating, description, stock, brand 
            FROM products 
            WHERE {where_clause}
            ORDER BY rating DESC, price ASC
            LIMIT 8
            """
            
            # Execute with parameters
            conn = sqlite3.connect(self.db.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql, params)
            results = cursor.fetchall()
            conn.close()
            
            if not results:
                return json.dumps([{"message": "No products found matching your criteria."}], indent=2)
            
            # Convert to list of dictionaries
            formatted = []
            for row in results:
                row_dict = dict(row)
                formatted.append(row_dict)
            
            return json.dumps(formatted, indent=2, ensure_ascii=False)
            
        except json.JSONDecodeError:
            return "Error: Invalid JSON format. Please provide valid JSON like: {\"budget\": 500, \"category\": \"electronics\"}"
        except Exception as e:
            return f"Recommendation error: {str(e)}"
    
    def chat(self, user_input: str) -> str:
        """Main chat method with error handling and logging"""
        try:
            print(f"\n🔍 Processing: '{user_input}'")
            
            # Clean and prepare input
            user_input = user_input.strip()
            
            # Quick response for simple greetings
            if user_input.lower() in ["hi", "hello", "hey"]:
                return "Hello! I'm your AI Shopping Assistant. How can I help you find products today?"
            
            # Process with agent
            result = self.agent_executor.invoke({"input": user_input})
            
            # Extract output
            response = result.get("output", "I apologize, but I couldn't process your request. Could you please rephrase?")
            
            # Log the interaction
            self.db.log_query(user_input, response[:1000])
            
            # Clean and format response
            response = self._format_response(response)
            
            return response
            
        except Exception as e:
            error_msg = f"I encountered an error: {str(e)[:100]}"
            print(f"❌ Agent error: {e}")
            return f"""{error_msg}

Please try one of these examples:
• "Show me laptops under $1500"
• "What's the weather in Tokyo?"
• "Recommend good headphones under $300"
• "Find gaming consoles with rating above 4.5"
• "Show me Apple products" """
    
    def _format_response(self, response: str) -> str:
        """Format the AI response for better readability"""
        # Remove any trailing ReAct format artifacts
        if "Final Answer:" in response:
            response = response.split("Final Answer:")[-1].strip()
        
        # Clean up any remaining Thought/Action patterns
        lines = response.split('\n')
        cleaned_lines = []
        for line in lines:
            if line.startswith("Thought:") or line.startswith("Action:") or line.startswith("Observation:"):
                continue
            cleaned_lines.append(line)
        response = '\n'.join(cleaned_lines).strip()
        
        # Parse and format JSON data if present
        if '[' in response and ']' in response:
            try:
                # Extract JSON portion
                json_start = response.find('[')
                json_end = response.rfind(']') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    data = json.loads(json_str)
                    
                    # Don't format if it's just an error message
                    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict) and "title" in data[0]:
                        # Format as readable output
                        formatted = "\n" + "="*60 + "\n"
                        formatted += "📦 **PRODUCT RESULTS**\n"
                        formatted += "="*60 + "\n"
                        
                        for i, item in enumerate(data, 1):
                            formatted += f"\n{i}. **{item.get('title', 'Unknown Product')}**\n"
                            
                            if 'brand' in item and item['brand']:
                                formatted += f"   🏷️  Brand: {item['brand']}\n"
                            
                            if 'price' in item:
                                price = item['price']
                                if isinstance(price, (int, float)):
                                    formatted += f"   💰 Price: ${price:.2f}\n"
                                else:
                                    formatted += f"   💰 Price: ${price}\n"
                            
                            if 'category' in item and item['category']:
                                formatted += f"   📂 Category: {item['category']}\n"
                            
                            if 'rating' in item:
                                rating = item['rating']
                                if isinstance(rating, (int, float)):
                                    stars = "⭐" * int(rating) + "☆" * (5 - int(rating))
                                    formatted += f"   ⭐ Rating: {rating:.1f}/5 {stars}\n"
                                else:
                                    formatted += f"   ⭐ Rating: {rating}/5\n"
                            
                            if 'stock' in item:
                                stock = str(item['stock'])
                                try:
                                    stock_int = int(stock.split()[0]) if stock.split()[0].isdigit() else 0
                                    if stock_int < 5:
                                        formatted += f"   ⚠️  Stock: {stock} (Low stock!)\n"
                                    else:
                                        formatted += f"   📦 Stock: {stock}\n"
                                except:
                                    formatted += f"   📦 Stock: {stock}\n"
                            
                            if 'description' in item and item['description']:
                                desc = item['description']
                                if len(desc) > 100:
                                    desc = desc[:100] + "..."
                                formatted += f"   📝 {desc}\n"
                            
                            if i < len(data):
                                formatted += "-"*50 + "\n"
                        
                        formatted += "="*60
                        
                        # Replace JSON with formatted version
                        before_json = response[:json_start].strip()
                        
                        if before_json:
                            response = before_json + "\n" + formatted
                        else:
                            response = formatted
            except:
                # If JSON parsing fails, return original response
                pass
        
        return response.strip()

# ======================
# 4. MAIN APPLICATION
# ======================
def check_ollama_health():
    """Check if Ollama is running and models are available"""
    try:
        # Check Ollama service
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code != 200:
            return False, "Ollama service not responding"
        
        # Check for available models
        models = response.json().get("models", [])
        if not models:
            return False, "No models found in Ollama"
        
        # List available models
        model_names = [model.get("name", "") for model in models]
        print(f"✅ Ollama running. Available models: {', '.join(model_names)}")
        
        # Check for recommended models
        recommended_models = ["llama3.1:8b", "llama3.1:latest", "llama3:8b", "mistral:latest", "qwen2:7b"]
        available_recommended = [m for m in recommended_models if any(m in name.lower() for name in model_names)]
        
        if available_recommended:
            print(f"💡 Recommended models available: {', '.join(available_recommended)}")
            return True, available_recommended[0]
        else:
            print(f"⚠️  Recommended models not found. Using first available: {model_names[0]}")
            return True, model_names[0]
            
    except requests.ConnectionError:
        return False, "Cannot connect to Ollama. Make sure it's running."
    except Exception as e:
        return False, f"Error: {str(e)}"

def main():
    print("=" * 70)
    print("🤖 INTELLIGENT SHOPPING ASSISTANT")
    print("=" * 70)
    print("\nPowered by Ollama & LangChain")
    print("Version 2.0 - Fixed Agent Initialization")
    
    # Check Ollama health
    print("\n🔍 Checking Ollama status...")
    ollama_ok, model_info = check_ollama_health()
    
    if not ollama_ok:
        print(f"\n❌ {model_info}")
        print("\n📋 SETUP INSTRUCTIONS:")
        print("1. Install Ollama: https://ollama.ai/")
        print("2. Start Ollama in terminal: `ollama serve`")
        print("3. In a NEW terminal, pull a model: `ollama pull llama3.1:8b`")
        print("4. Wait for download to complete")
        print("5. Run this script again")
        print("\n💡 Quick test: Open browser to http://localhost:11434/")
        return
    
    print(f"\n✅ Using model: {model_info}")
    
    print("\n🎯 I can help you with:")
    print("  1. 🛒 Smart product search and recommendations")
    print("  2. 🌤️ Weather-aware shopping advice")
    print("  3. 💰 Budget planning and price comparisons")
    print("  4. ⭐ Product comparisons and reviews")
    print("  5. 📊 Stock availability and alerts")
    
    print("\n💡 Try these queries:")
    print("  • 'Find gaming laptops under $2000 with good reviews'")
    print("  • 'What should I buy for camping in warm weather?'")
    print("  • 'Show me Sony headphones'")
    print("  • 'Weather in London and indoor activity suggestions'")
    print("  • 'Recommend kitchen appliances under $200'")
    
    print("\n" + "-"*70)
    
    # Initialize agent
    try:
        agent = SmartShoppingAgent(model_name=model_info)
        print("✅ Shopping Agent initialized successfully!")
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        print("\n🔧 TROUBLESHOOTING:")
        print("1. Ensure Ollama is running: Open terminal, run `ollama serve`")
        print("2. Check available models: `ollama list`")
        print("3. Try a smaller model: `ollama pull llama3.1:8b` (recommended)")
        print("4. Check Python packages: `pip install langchain langchain-community`")
        print("5. Restart Ollama: `pkill -f ollama` then `ollama serve`")
        return
    
    print("-"*70)
    print("Commands: 'quit' to exit | 'help' for tips | 'examples' for ideas")
    print("="*70 + "\n")
    
    # Interactive chat
    conversation_count = 0
    while True:
        try:
            user_input = input("👤 You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'bye', 'q']:
                print(f"\n👋 Thank you for chatting! You had {conversation_count} conversations.")
                print("Goodbye!\n")
                break
            
            if user_input.lower() == 'help':
                print("\n💡 **HOW TO GET BEST RESULTS:**")
                print("  • Be specific: 'gaming laptops under $1500'")
                print("  • Include budget: 'phones around $800'")
                print("  • Add preferences: 'noise cancelling headphones'")
                print("  • Combine needs: 'weather in Paris and indoor activities'")
                print("  • Use natural language: 'what are good gifts for a tech enthusiast?'")
                print("\n📊 **AVAILABLE CATEGORIES:**")
                print("  Electronics, Computers, Audio, Home Theater, Footwear,")
                print("  Clothing, Watches, Home Appliances, Kitchen, Gaming")
                continue
            
            if user_input.lower() == 'examples':
                print("\n🎯 **EXAMPLE QUERIES:**")
                print("  • 'Show me the top rated electronics under $1000'")
                print("  • 'What are good gifts under $100?'")
                print("  • 'Check weather in Dubai and suggest appropriate products'")
                print("  • 'Find Apple products'")
                print("  • 'Recommend home appliances for a rainy weekend'")
                print("  • 'What should I wear in cold weather?'")
                print("  • 'Show me products with low stock'")
                continue
            
            print("\n🤔 Thinking...")
            
            # Get AI response
            start_time = time.time()
            response = agent.chat(user_input)
            processing_time = time.time() - start_time
            
            conversation_count += 1
            
            print(f"\n🤖 Assistant (processed in {processing_time:.1f}s):")
            print("-" * 60)
            print(response)
            print("-" * 60 + "\n")
            
        except KeyboardInterrupt:
            print(f"\n\n👋 Session ended. Total conversations: {conversation_count}")
            print("Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            print("Please try again or type 'help' for tips.\n")

if __name__ == "__main__":
    main()