import os
import json
import sqlite3
import requests
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime
import time
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.llms import Ollama
from langchain_core.tools import Tool
from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate, MessagesPlaceholder
from langchain_classic.memory import ConversationBufferMemory
import streamlit as st



# ======================
# 1. CSV PRODUCTS DATABASE (Direct CSV Operations)
# ======================
class ProductDatabase:
    def __init__(self, csv_path: str = r"D:\sql agent MCP\Message Group - Product.csv"):
        self.csv_path = csv_path
        self.df = None
        self._load_csv()
    
    def _load_csv(self):
        """Load products from CSV file"""
        try:
            # Read CSV file
            self.df = pd.read_csv(self.csv_path, encoding='utf-8')
            
            # Clean column names
            self.df.columns = self.df.columns.str.strip()
            
            # Rename columns to standard schema
            column_mapping = {
                'S.No': 'sno',
                'Product ID': 'product_id',
                'Product Name': 'product_name',
                'Brand Desc': 'brand_desc',
                'Product Size': 'product_size',
                'Currancy': 'currency',
                'MRP': 'mrp',
                'SellPrice': 'sell_price',
                'Discount': 'discount',
                'Category': 'category'
            }
            
            self.df.rename(columns=column_mapping, inplace=True)
            
            # Clean numeric columns
            self.df['mrp'] = pd.to_numeric(self.df['mrp'], errors='coerce')
            self.df['sell_price'] = pd.to_numeric(self.df['sell_price'], errors='coerce')
            
            # Fill NaN values
            self.df = self.df.fillna('')
            
            # Remove duplicates based on product_id
            self.df = self.df.drop_duplicates(subset=['product_id'], keep='first')
            
        except FileNotFoundError:
            self._create_sample_data()
        except Exception as e:
            self._create_sample_data()
    
    def _create_sample_data(self):
        """Create sample data based on CSV structure"""
        sample_products = [
            {
                'sno': 1, 'product_id': 'FR001', 'product_name': 'ekw eau de cologne 400 ml',
                'brand_desc': 'Cologne Fragrance', 'product_size': 'Small', 'currency': 'Rs.',
                'mrp': 3900, 'sell_price': 3120, 'discount': '20% off', 'category': 'Fragrance-Women'
            },
            {
                'sno': 2, 'product_id': 'DRW1', 'product_name': 'womens v-neck short dress - yellow',
                'brand_desc': 'DRW1 - Westernwear-Women', 'product_size': 'Size:Medium,Small,X-Large,XX-Large',
                'currency': 'Rs.', 'mrp': 1899, 'sell_price': 569, 'discount': '70% off', 'category': 'Westernwear-Women'
            },
            {
                'sno': 3, 'product_id': 'DRW2', 'product_name': 'womens round neck solid top - black',
                'brand_desc': 'DRW2 - Westernwear-Women', 'product_size': 'Size:Large,Medium,Small,X-Large',
                'currency': 'Rs.', 'mrp': 1499, 'sell_price': 599, 'discount': '60% off', 'category': 'Westernwear-Women'
            },
            {
                'sno': 4, 'product_id': 'DRW3', 'product_name': 'womens round neck stripe shift dress - red',
                'brand_desc': 'DRW3 - Westernwear-Women', 'product_size': 'Size:Medium,Small',
                'currency': 'Rs.', 'mrp': 1599, 'sell_price': 639, 'discount': '60% off', 'category': 'Westernwear-Women'
            },
        ]
        
        self.df = pd.DataFrame(sample_products)
    
    def search_products(self, query_params: Dict[str, Any]) -> str:
        """
        Search products using query parameters
        
        Supported parameters:
        - search_text: text to search in product_name
        - category: category filter
        - min_price: minimum sell_price
        - max_price: maximum sell_price
        - discount_contains: text in discount field
        - brand: brand filter
        - sort_by: column to sort by (default: sell_price)
        - limit: max results (default: 20)
        """
        try:
            result_df = self.df.copy()
            
            # Text search in product name
            if 'search_text' in query_params and query_params['search_text']:
                search_text = str(query_params['search_text']).lower()
                result_df = result_df[result_df['product_name'].str.lower().str.contains(search_text, na=False)]
            
            # Category filter
            if 'category' in query_params and query_params['category']:
                category = str(query_params['category']).lower()
                result_df = result_df[result_df['category'].str.lower().str.contains(category, na=False)]
            
            # Brand filter
            if 'brand' in query_params and query_params['brand']:
                brand = str(query_params['brand']).lower()
                result_df = result_df[result_df['brand_desc'].str.lower().str.contains(brand, na=False)]
            
            # Price range filters
            if 'min_price' in query_params and query_params['min_price'] is not None:
                result_df = result_df[result_df['sell_price'] >= float(query_params['min_price'])]
            
            if 'max_price' in query_params and query_params['max_price'] is not None:
                result_df = result_df[result_df['sell_price'] <= float(query_params['max_price'])]
            
            # Discount filter
            if 'discount_contains' in query_params and query_params['discount_contains']:
                discount_text = str(query_params['discount_contains']).lower()
                result_df = result_df[result_df['discount'].str.lower().str.contains(discount_text, na=False)]
            
            # Sort results
            sort_by = query_params.get('sort_by', 'sell_price')
            if sort_by in result_df.columns:
                result_df = result_df.sort_values(by=sort_by)
            
            # Limit results
            limit = int(query_params.get('limit', 20))
            result_df = result_df.head(limit)
            
            if len(result_df) == 0:
                return "No products found matching your criteria."
            
            # Convert to list of dictionaries
            results = result_df.to_dict('records')
            
            return json.dumps(results, indent=2, ensure_ascii=False)
                
        except Exception as e:
            return f"❌ Error searching products: {str(e)}"
    
    def get_categories(self) -> List[str]:
        """Get all available categories"""
        try:
            categories = self.df['category'].dropna().unique().tolist()
            return sorted([cat for cat in categories if cat])
        except:
            return []
    
    def get_brands(self) -> List[str]:
        """Get all available brands from brand_desc"""
        try:
            brands = self.df['brand_desc'].dropna().unique().tolist()
            return sorted([brand for brand in brands if brand])[:50]  # Limit to 50
        except:
            return []


# ======================
# 2. SHOPPING AGENT WITH GEMINI
# ======================
class SmartShoppingAgent:
    def __init__(self, api_key: str):
        """Initialize the shopping agent with Gemini"""
        self.db = ProductDatabase()
        
        # Configure Gemini API
        genai.configure(api_key=api_key)
        
        # Initialize Gemini with LangChain wrapper
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0.1,
            convert_system_message_to_human=True
        )
        
        # Get available categories and brands
        self.categories = self.db.get_categories()
        self.brands = self.db.get_brands()
        
        # Create tools
        self.tools = [
            Tool(
                name="SearchProducts",
                func=self._query_products,
                description=f"""Search products from CSV using query parameters.

DATABASE SCHEMA:
- Columns: sno, product_id, product_name, brand_desc, product_size, currency, mrp, sell_price, discount, category

AVAILABLE CATEGORIES: {', '.join(self.categories[:10])}
AVAILABLE BRANDS: {', '.join(self.brands[:15])}

INPUT FORMAT: JSON object with these optional parameters:
- search_text: text to search in product name (e.g., "dress", "cologne")
- category: category to filter (e.g., "women", "fragrance")
- brand: brand to filter
- min_price: minimum price
- max_price: maximum price
- discount_contains: discount text (e.g., "70%")
- sort_by: column to sort by (default: "sell_price")
- limit: max results (default: 20)

CORRECT EXAMPLES:
1. Search dresses: {{"search_text": "dress", "limit": 10}}
2. Price range: {{"min_price": 500, "max_price": 1000, "sort_by": "sell_price", "limit": 15}}
3. Category: {{"category": "women", "sort_by": "sell_price", "limit": 10}}
4. Discount: {{"discount_contains": "70%", "limit": 10}}
5. Combined: {{"search_text": "dress", "max_price": 1000, "category": "women", "limit": 15}}
"""
            ),
        ]
        
        # Strict ReAct prompt
        prompt_template = """You are a precise shopping assistant. Your ONLY job is to help users find products from the CSV database.

STRICT OPERATIONAL RULES:
1. You MUST use the SearchProducts tool for ALL product queries
2. You MUST provide input as a JSON object with proper parameters
3. Always include "limit" parameter (typically 10-20)
4. For text searches, use "search_text" parameter
5. For price queries, use "min_price" and/or "max_price"
6. For category/brand, use "category" or "brand" parameters
7. DO NOT make up product information - only use database results

RESPONSE FORMAT - FOLLOW EXACTLY:

Question: [user's question]
Thought: [what the user wants - identify search_text, price range, category, etc.]
Action: SearchProducts
Action Input: {{"search_text": "value", "max_price": 1000, "limit": 15}}
Observation: [database results]
Thought: I have the database results
Final Answer: [present results clearly with product names, prices, and discounts but if asked for product or item answer about only product in a sentence for example cheapest product is product_name. If asked on price answer  product and price.]

Available tools: {tools}
Tool names: {tool_names}

Question: {input}
{agent_scratchpad}"""
        
        self.prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["input", "agent_scratchpad", "tools", "tool_names"]
        )
        
        # Create agent
        self.agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        
        # Create executor with strict settings
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=False,  # Disabled to prevent CLI output
            max_iterations=3,
            handle_parsing_errors=True,
            return_intermediate_steps=False,
            early_stopping_method="force"
        )
    
    def _query_products(self, query_input: str) -> str:
        """Execute product query with JSON parameters"""
        try:
            # Parse JSON input
            query_params = json.loads(query_input)
            
            # Ensure limit is set
            if 'limit' not in query_params:
                query_params['limit'] = 20
            
            return self.db.search_products(query_params)
            
        except json.JSONDecodeError:
            return "ERROR: Input must be a valid JSON object. Example: {\"search_text\": \"dress\", \"limit\": 10}"
        except Exception as e:
            return f"ERROR: {str(e)}"
    
    def chat(self, user_input: str) -> str:
        """Main chat method"""
        try:
            user_input = user_input.strip()
            
            # Quick responses
            if user_input.lower() in ["hi", "hello", "hey"]:
                return f"Hello! I can help you find products. We have {len(self.categories)} categories including: {', '.join(self.categories[:5])}. What are you looking for?"
            
            # Process with agent
            result = self.agent_executor.invoke({"input": user_input})
            response = result.get("output", "I couldn't find that. Please try: 'show me dresses' or 'products under 1000'")
            
            # Format response
            response = self._format_response(response)
            
            return response
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return f"""❌ **Error Details:**
```
{str(e)}

{error_details}
```

**Please try:**
- "Show me women's dresses"
- "Products under 1000"
- "What products do you have?"
- "Show fragrance products"
"""
    
    def _format_response(self, response: str) -> str:
        """Format AI response for readability"""
        # Remove ReAct artifacts
        if "Final Answer:" in response:
            response = response.split("Final Answer:")[-1].strip()
        
        # Clean up
        lines = response.split('\n')
        cleaned_lines = []
        for line in lines:
            if any(line.startswith(prefix) for prefix in ["Thought:", "Action:", "Observation:", "Action Input:"]):
                continue
            cleaned_lines.append(line)
        response = '\n'.join(cleaned_lines).strip()
        
        # Format JSON data if present
        if '[' in response and ']' in response:
            try:
                json_start = response.find('[')
                json_end = response.rfind(']') + 1
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
                
                if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                    formatted = "\n" + "="*70 + "\n"
                    formatted += "🛍️  PRODUCTS FOUND\n"
                    formatted += "="*70 + "\n"
                    
                    for i, item in enumerate(data, 1):
                        formatted += f"\n{i}. {item.get('product_name', 'Unknown Product')}\n"
                        
                        if 'sell_price' in item:
                            currency = item.get('currency', 'Rs.')
                            sell_price = item['sell_price']
                            formatted += f"   💰 Price: {currency} {sell_price:,.0f}\n"
                        
                        if 'mrp' in item and item.get('mrp'):
                            mrp = item['mrp']
                            formatted += f"   🏷️  MRP: {currency} {mrp:,.0f}\n"
                        
                        if 'discount' in item and item['discount']:
                            formatted += f"   🎯 Discount: {item['discount']}\n"
                        
                        if 'category' in item and item['category']:
                            formatted += f"   📂 Category: {item['category']}\n"
                        
                        if 'product_size' in item and item['product_size']:
                            formatted += f"   📏 Sizes: {item['product_size']}\n"
                        
                        if 'brand_desc' in item and item['brand_desc']:
                            desc = item['brand_desc']
                            if len(desc) > 80:
                                desc = desc[:80] + "..."
                            formatted += f"   📝 {desc}\n"
                        
                        if i < len(data):
                            formatted += "-"*70 + "\n"
                    
                    formatted += "="*70
                    
                    before_json = response[:json_start].strip()
                    response = (before_json + "\n" + formatted) if before_json else formatted
            except:
                pass
        
        return response.strip()


# ======================
# 3. STREAMLIT APPLICATION
# ======================
def main():
    # Page configuration
    st.set_page_config(
        page_title="Shopping Assistant",
        page_icon="🛍️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
        <style>
        .main {
            padding: 1rem;
        }
        .stTextInput > div > div > input {
            font-size: 16px;
        }
        .chat-message {
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
        }
        .user-message {
            background-color: #e3f2fd;
        }
        .assistant-message {
            background-color: #f5f5f5;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Title
    st.title("🛍️ Shopping Assistant - Powered by Gemini AI")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Get API key from environment
        api_key = "key"
        
        if api_key:
            st.success("✅ API Key loaded from environment")
        else:
            st.error("❌ GEMINI_API_KEY not found in environment variables")
            st.info("Please set GEMINI_API_KEY in your environment")
        
        st.markdown("---")
        
        # Information
        st.header("ℹ️ Information")
        st.markdown("""
        **Example Queries:**
        - Show me women's dresses
        - Products under 1000 rupees
        - Show fragrance products
        - Cheapest products available
        - Products with 70% discount
        """)
        
        st.markdown("---")
        
        # Statistics placeholder
        stats_placeholder = st.empty()
    
    # Initialize session state
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    if 'agent' not in st.session_state:
        st.session_state.agent = None
    
    if 'initialized' not in st.session_state:
        st.session_state.initialized = False
    
    # Initialize agent
    if api_key and not st.session_state.initialized:
        with st.spinner("🔄 Initializing Gemini agent..."):
            try:
                st.session_state.agent = SmartShoppingAgent(api_key=api_key)
                st.session_state.initialized = True
                st.success("✅ Agent ready!")
                
                # Update sidebar stats
                with stats_placeholder:
                    st.metric("Categories", len(st.session_state.agent.categories))
                    st.metric("Brands", len(st.session_state.agent.brands))
                    
            except Exception as e:
                st.error(f"❌ Failed to initialize agent: {e}")
                st.session_state.initialized = False
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.container():
            if message["role"] == "user":
                st.markdown(f'<div class="chat-message user-message">👤 **You:** {message["content"]}</div>', 
                           unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-message assistant-message">🤖 **Assistant:**\n\n{message["content"]}</div>', 
                           unsafe_allow_html=True)
    
    # Chat input
    if st.session_state.initialized and st.session_state.agent:
        # Quick action buttons
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🔍 View Categories"):
                categories = st.session_state.agent.categories
                category_text = f"**Available Categories ({len(categories)}):**\n\n" + "\n".join([f"• {cat}" for cat in categories])
                st.session_state.messages.append({"role": "assistant", "content": category_text})
                st.rerun()
        
        with col2:
            if st.button("🏷️ View Brands"):
                brands = st.session_state.agent.brands[:30]
                brand_text = f"**Available Brands ({len(st.session_state.agent.brands)}):**\n\n" + "\n".join([f"{i+1}. {brand}" for i, brand in enumerate(brands)])
                if len(st.session_state.agent.brands) > 30:
                    brand_text += f"\n\n... and {len(st.session_state.agent.brands)-30} more"
                st.session_state.messages.append({"role": "assistant", "content": brand_text})
                st.rerun()
        
        with col3:
            if st.button("💬 Example Query"):
                example = "Show me women's dresses under 1000"
                st.session_state.messages.append({"role": "user", "content": example})
                
                with st.spinner("🤔 Thinking..."):
                    start_time = time.time()
                    response = st.session_state.agent.chat(example)
                    processing_time = time.time() - start_time
                    response += f"\n\n*Processing time: {processing_time:.1f}s*"
                
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.rerun()
        
        with col4:
            if st.button("🗑️ Clear Chat"):
                st.session_state.messages = []
                st.rerun()
        
        st.markdown("---")
        
        # Chat input form
        with st.form(key="chat_form", clear_on_submit=True):
            user_input = st.text_input(
                "Ask me about products...",
                placeholder="e.g., Show me women's dresses under 1000",
                key="user_input"
            )
            submit_button = st.form_submit_button("Send 🚀")
        
        if submit_button and user_input:
            # Add user message
            st.session_state.messages.append({"role": "user", "content": user_input})
            
            # Get agent response
            with st.spinner("🤔 Thinking..."):
                start_time = time.time()
                response = st.session_state.agent.chat(user_input)
                processing_time = time.time() - start_time
                response += f"\n\n*Processing time: {processing_time:.1f}s*"
            
            # Add assistant message
            st.session_state.messages.append({"role": "assistant", "content": response})
            
            # Rerun to update chat
            st.rerun()
    
    else:
        st.info("⚠️ Please set GEMINI_API_KEY environment variable to start chatting")
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666;'>
            <small>Powered by Google Gemini 2.0 Flash | Version 5.0</small>
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
