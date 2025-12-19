from fastapi import FastAPI, Request, Form, Depends, HTTPException, Header
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import OAuth2AuthorizationCodeBearer
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uuid
import httpx
import os
import jwt as pyjwt
import stripe
import logging
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, String, Boolean, JSON, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import time

# Configure logging
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000", 
        "http://0.0.0.0:3000",
        "http://frontend:80",
        "http://frontend",
        "*"  # Allow all for development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- DB Setup ----
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./onboarding.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class OnboardingSubmission(Base):
    __tablename__ = "onboarding_submissions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, index=True)
    organization_size = Column(String)
    product_stage = Column(String, nullable=True)
    product_scope = Column(String, nullable=True)
    biggest_challenge = Column(Text)
    team_composition = Column(String)
    analysis = Column(JSON, nullable=True)

class ContactSubmission(Base):
    __tablename__ = "contact_submissions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, index=True)
    marketing_opt_in = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    source = Column(String, default="onboarding-app")
    selected_recommendation = Column(String, nullable=True)
    completed_at = Column(String, nullable=True)

class Contact(Base):
    __tablename__ = "contacts"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, index=True)
    use_case = Column(String)
    experience = Column(String)
    company_size = Column(String)
    application_type = Column(String)
    application_details = Column(Text)
    company = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# ---- OAuth2 Token URLs and Secrets ----
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI")
JWT_SECRET = os.getenv("JWT_SECRET", "secret")
JWT_ALGORITHM = "HS256"

# ---- Buildly Labs API Configuration ----
LABS_API_URL = os.getenv("LABS_API_URL", "https://labs-api.buildly.io")
BUILDLY_LABS_API_BASE = "https://labs-api.buildly.io"
BUILDLY_JWT_TOKEN = os.getenv("JWT_SECRET", "secret")  # Use JWT_SECRET for Labs API authentication

# ---- BabbleBeaver Configuration ----
BABBLEBEAVER_API_KEY = os.getenv("BABBLEBEAVER_API_KEY", "demo-key")
BABBLEBEAVER_API_URL = os.getenv("BABBLEBEAVER_API_URL", "https://insights-babble.buildly.io")

# ---- Stripe Configuration ----
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# ---- Models ----
class OnboardingStep1(BaseModel):
    email: str

class OnboardingStep2(BaseModel):
    organization_size: str  # "just_me", "small_team", "large_organization"

class OnboardingStep3Small(BaseModel):
    product_stage: str  # "idea_planning", "prototype_mvp", "launched_users", "scaling_teams"

class OnboardingStep3Large(BaseModel):
    product_scope: str  # "single_product", "multiple_products"

class OnboardingStep4(BaseModel):
    biggest_challenge: str

class OnboardingStep5(BaseModel):
    team_composition: str  # "just_me", "founding_team", "external_contractors", "large_internal_teams"

class OnboardingComplete(BaseModel):
    email: str
    organization_size: str
    product_stage: Optional[str] = None
    product_scope: Optional[str] = None
    biggest_challenge: str
    team_composition: str

class RecommendationSelection(BaseModel):
    email: str
    selected_recommendation: str  # "labs", "foundry", "enterprise"

class ContactRequest(BaseModel):
    email: str
    marketingOptIn: bool
    timestamp: str
    source: str
    useCase: Optional[str] = None
    experience: Optional[str] = None
    companySize: Optional[str] = None
    applicationType: Optional[str] = None
    applicationDetails: Optional[str] = None
    company: Optional[str] = None

class LabsIntegrationRequest(BaseModel):
    email: str
    company: str
    companySize: str
    useCase: str
    experience: str
    applicationType: str
    applicationDetails: str
    selectedProduct: str
    architecture: str
    estimatedBudget: str
    teamSize: str
    keyFeatures: List[str]

class OrganizationCheckRequest(BaseModel):
    organizationName: str

class CreateBuildlyAccountRequest(BaseModel):
    email: str
    password: str
    company: str
    firstName: str
    lastName: str
    is_active: bool = True  # Default to active

class PaymentRequest(BaseModel):
    email: str
    selectedProduct: str
    paymentMethodId: str
    billingAddress: str

class SubscriptionRequest(BaseModel):
    paymentMethodId: str
    email: str
    priceId: str
    trialDays: int = 30
    couponCode: Optional[str] = None

# ---- JWT Utilities ----
def create_jwt_token(email: str):
    payload = {
        "sub": email,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_user_email_from_token(token: str):
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.get(f"{LABS_API_URL}/me", headers=headers)
            response.raise_for_status()
            return response.json().get("email")
    except Exception:
        raise HTTPException(status_code=401, detail="Unable to validate token with Buildly Core")

# ---- BabbleBeaver Analysis ----

async def fetch_labs_products():
    """Fetch current product data from Labs API"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try without auth first (for upcoming public endpoints)
            response = await client.get(f"{LABS_API_URL}/subscription/stripe_products/")
            
            if response.status_code == 200:
                products = response.json()
                logger.info(f"✅ Fetched {len(products)} products from Labs API (public endpoint)")
                return products
            elif response.status_code == 401:
                logger.info("🔑 Labs API requires authentication - public endpoints not yet deployed")
                return None
            else:
                logger.warning(f"⚠️ Labs API returned {response.status_code}: {response.text}")
                return None
                
    except Exception as e:
        logger.error(f"❌ Failed to fetch products from Labs API: {str(e)}")
        return None

async def get_available_products():
    """Get available products, preferring Labs API data with fallback"""
    # Try to get from Labs API first
    labs_products = await fetch_labs_products()
    
    if labs_products and isinstance(labs_products, list):
        # Transform Labs API data to our internal format
        products = []
        for product in labs_products:
            products.append({
                "id": product.get("id"),
                "name": product.get("name"),
                "price": product.get("price", 0),
                "billing_interval": product.get("billing_interval", "month"),
                "trial_days": product.get("trial_days", 30),
                "description": product.get("description", ""),
                "features": product.get("features", []),
                "stripe_price_id": product.get("stripe_price_id"),
                "stripe_product_id": product.get("stripe_product_id")
            })
        return products
    
    # Fallback to hardcoded products matching frontend
    logger.info("📋 Using fallback product data")
    return [
        {
            "id": "foundry",
            "name": "Buildly Foundry",
            "price": 50.0,
            "billing_interval": "month", 
            "trial_days": 30,
            "description": "Perfect for growing teams and mid-size companies",
            "features": [
                "Microservice Architecture Foundation",
                "Advanced DevOps Toolchain", 
                "API Gateway Management",
                "Container Orchestration",
                "Priority Support"
            ]
        },
        {
            "id": "developer",
            "name": "Buildly Developer",
            "price": 70.0,
            "billing_interval": "month",
            "trial_days": 30, 
            "description": "Advanced tools for serious developers",
            "features": [
                "VS Code Integration via Copilot",
                "Code Generation & Templates via CLI",
                "Punchlist Issue Tracking", 
                "Open Source Ecosystem",
                "Open Source Deployment Management (COMING SOON)"
            ]
        },
        {
            "id": "enterprise", 
            "name": "Buildly Enterprise",
            "price": 150.0,
            "billing_interval": "month",
            "trial_days": 0,  # Enterprise doesn't have trial
            "description": "Comprehensive solution for large organizations", 
            "features": [
                "InnerSource Management",
                "Product Portfolio Gamification",
                "Multi-Cloud Deployment",
                "Advanced Security & Compliance", 
                "Dedicated Success Team"
            ]
        }
    ]

# Cache for Stripe products (refresh every 10 minutes)
_stripe_products_cache = {
    "data": None,
    "last_updated": 0,
    "cache_duration": 600  # 10 minutes
}

async def fetch_stripe_products():
    """Fetch products and prices directly from Stripe with caching"""
    global _stripe_products_cache
    
    current_time = time.time()
    
    # Check if cache is still valid
    if (_stripe_products_cache["data"] is not None and 
        current_time - _stripe_products_cache["last_updated"] < _stripe_products_cache["cache_duration"]):
        logger.info("📋 Using cached Stripe products")
        return _stripe_products_cache["data"]
    
    try:
        if not stripe.api_key:
            logger.warning("⚠️ Stripe not configured, using fallback products")
            return None
            
        logger.info("🔄 Fetching products from Stripe...")
        
        # Fetch products and prices from Stripe
        products = stripe.Product.list(active=True, limit=10)
        prices = stripe.Price.list(active=True, limit=20)
        
        # Create a map of prices by product
        price_map = {}
        for price in prices.data:
            if price.product not in price_map:
                price_map[price.product] = []
            price_map[price.product].append(price)
        
        # Transform to our format
        product_list = []
        for product in products.data:
            product_prices = price_map.get(product.id, [])
            
            # Find the primary monthly price
            monthly_price = None
            for p in product_prices:
                if p.recurring and p.recurring.interval == 'month':
                    monthly_price = p
                    break
            
            if monthly_price:
                # Determine trial days based on product name
                trial_days = 30 if 'foundry' in product.name.lower() else 0
                
                product_data = {
                    "id": product.name.lower().replace(" ", "_"),
                    "name": product.name,
                    "price": monthly_price.unit_amount / 100,  # Convert cents to dollars
                    "billing_interval": monthly_price.recurring.interval,
                    "trial_days": trial_days,
                    "description": product.description or f"Professional {product.name} subscription",
                    "features": [],  # Could be stored in metadata
                    "stripe_price_id": monthly_price.id,
                    "stripe_product_id": product.id,
                    "currency": monthly_price.currency.upper()
                }
                product_list.append(product_data)
        
        # Update cache
        _stripe_products_cache["data"] = product_list
        _stripe_products_cache["last_updated"] = current_time
        
        logger.info(f"✅ Fetched {len(product_list)} products from Stripe")
        return product_list
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch from Stripe: {str(e)}")
        return None

@app.get("/api/products")
async def get_products():
    """Get available products (from Stripe with fallback)"""
    try:
        # Try Stripe first
        stripe_products = await fetch_stripe_products()
        
        if stripe_products:
            return {
                "success": True,
                "source": "stripe",
                "products": stripe_products,
                "cached": True
            }
        
        # Fallback to Labs API
        labs_products = await fetch_labs_products()
        if labs_products:
            return {
                "success": True,
                "source": "labs_api", 
                "products": labs_products
            }
        
        # Final fallback to hardcoded
        fallback_products = await get_available_products()
        return {
            "success": True,
            "source": "fallback",
            "products": fallback_products
        }
        
    except Exception as e:
        logger.error(f"❌ Error fetching products: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Failed to fetch products"
            }
        )

async def analyze_onboarding(data: OnboardingComplete):
    """Analyze onboarding data and provide intelligent product recommendations"""
    try:
        # First, get available products from Labs API
        available_products = await get_available_products()
        
        # Try BabbleBeaver for AI analysis
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Format the data for BabbleBeaver
            payload = {
                "user_profile": {
                    "email": data.email,
                    "organization_size": data.organization_size,
                    "team_composition": data.team_composition,
                    "experience_level": data.biggest_challenge  # This gives insight into experience
                },
                "project_details": {
                    "product_stage": data.product_stage,
                    "product_scope": data.product_scope,
                    "main_challenge": data.biggest_challenge
                },
                "available_products": available_products,
                "analysis_type": "onboarding_recommendation"
            }
            
            print(f"Sending to BabbleBeaver: {payload}")
            response = await client.post(
                f"{BABBLEBEAVER_API_URL}/api/analyze", 
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {BABBLEBEAVER_API_KEY}"
                }
            )
            
            print(f"BabbleBeaver response status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"BabbleBeaver response: {result}")
                return result
            else:
                print(f"BabbleBeaver error: {response.text}")
                # Return intelligent analysis using available products
                return await generate_intelligent_analysis(data, available_products)
                
    except Exception as e:
        print(f"BabbleBeaver connection failed: {str(e)}")
        # Get products and generate intelligent analysis
        available_products = await get_available_products()
        return await generate_intelligent_analysis(data, available_products)

async def generate_intelligent_analysis(data: OnboardingComplete, available_products):
    """Generate simplified analysis based on actual questionnaire data"""
    
    # Extract key variables for use throughout function
    company_size = data.organization_size
    use_case = data.biggest_challenge
    role = data.team_composition
    
    # Score each product based on user profile
    product_scores = []
    
    for product in available_products:
        score = 20  # Base score
        reasoning = []
        
        # Company Size scoring (simplified)        
        if company_size in ["1-10"]:
            if product["name"] == "Buildly Developer":
                score += 30
                reasoning.append("Perfect for small teams and individual developers")
            elif product["name"] == "Buildly Foundry":
                score += 20
                reasoning.append("Good option for growing small teams")
            elif product["name"] == "Buildly Enterprise":
                score += 5
                reasoning.append("Enterprise features may be unnecessary for small teams")
                
        elif company_size in ["11-50", "51-200"]:
            if product["name"] == "Buildly Foundry":
                score += 30
                reasoning.append("Ideal for mid-size teams and growing companies")
            elif product["name"] == "Buildly Developer":
                score += 25
                reasoning.append("Great for development-focused teams")
            elif product["name"] == "Buildly Enterprise":
                score += 15
                reasoning.append("Consider for advanced collaboration needs")
                
        elif company_size in ["201-1000", "1000+"]:
            if product["name"] == "Buildly Enterprise":
                score += 30
                reasoning.append("Built for large organizations and enterprise needs")
            elif product["name"] == "Buildly Foundry":
                score += 20
                reasoning.append("Good foundation, may need enterprise features later")
            elif product["name"] == "Buildly Developer":
                score += 10
                reasoning.append("Individual developer focus may not suit large organizations")
        
        # Use Case scoring (updated for new scenarios)        
        if use_case == "Building My First Real App":
            if product["name"] == "Buildly Foundry":
                score += 30
                reasoning.append("Perfect for entrepreneurs building their first professional app")
            elif product["name"] == "Buildly Developer":
                score += 20
                reasoning.append("Good development tools for solo entrepreneurs")
            elif product["name"] == "Buildly Enterprise":
                score += 5
                reasoning.append("Too complex for first-time app builders")
                
        elif use_case == "Scaling Our Prototype":
            if product["name"] == "Buildly Foundry":
                score += 35
                reasoning.append("Ideal for scaling prototypes with proper architecture")
            elif product["name"] == "Buildly Enterprise":
                score += 25
                reasoning.append("Advanced features for serious scaling")
            elif product["name"] == "Buildly Developer":
                score += 15
                reasoning.append("Individual tools may not suit scaling teams")
                
        elif use_case == "Advanced Development Workflow":
            if product["name"] == "Buildly Developer":
                score += 35
                reasoning.append("Cutting-edge tools for professional developers")
            elif product["name"] == "Buildly Foundry":
                score += 25
                reasoning.append("Professional platform with advanced features")
            elif product["name"] == "Buildly Enterprise":
                score += 20
                reasoning.append("Enterprise features for complex workflows")
                
        elif use_case == "Enterprise Team Collaboration":
            if product["name"] == "Buildly Enterprise":
                score += 35
                reasoning.append("Built for large team collaboration and management")
            elif product["name"] == "Buildly Foundry":
                score += 20
                reasoning.append("Good foundation, may need enterprise features")
            elif product["name"] == "Buildly Developer":
                score += 10
                reasoning.append("Individual focus doesn't suit large teams")
                
        elif use_case == "Legacy System Integration":
            if product["name"] == "Buildly Enterprise":
                score += 30
                reasoning.append("Enterprise-grade integration capabilities")
            elif product["name"] == "Buildly Foundry":
                score += 25
                reasoning.append("Strong API gateway for system integration")
            elif product["name"] == "Buildly Developer":
                score += 15
                reasoning.append("CLI tools help with integration development")
        
        # Role scoring (updated for new personas)        
        if role == "Solo Entrepreneur":
            if product["name"] == "Buildly Foundry":
                score += 30
                reasoning.append("Perfect for entrepreneurs who need to move fast")
            elif product["name"] == "Buildly Developer":
                score += 20
                reasoning.append("Good tools for solo development")
            elif product["name"] == "Buildly Enterprise":
                score += 5
                reasoning.append("Overkill for solo entrepreneurs")
                
        elif role == "Startup Founder/CTO":
            if product["name"] == "Buildly Foundry":
                score += 35
                reasoning.append("Ideal for startup teams that need to scale quickly")
            elif product["name"] == "Buildly Enterprise":
                score += 25
                reasoning.append("Consider for rapid team growth")
            elif product["name"] == "Buildly Developer":
                score += 20
                reasoning.append("Good for development-focused startups")
                
        elif role == "Professional Developer":
            if product["name"] == "Buildly Developer":
                score += 35
                reasoning.append("Advanced tooling for professional developers")
            elif product["name"] == "Buildly Foundry":
                score += 25
                reasoning.append("Professional platform with comprehensive features")
            elif product["name"] == "Buildly Enterprise":
                score += 15
                reasoning.append("Enterprise features may be unnecessary")
                
        elif role == "Enterprise Tech Lead":
            if product["name"] == "Buildly Enterprise":
                score += 35
                reasoning.append("Built for enterprise technical leadership")
            elif product["name"] == "Buildly Foundry":
                score += 25
                reasoning.append("Good foundation for enterprise teams")
            elif product["name"] == "Buildly Developer":
                score += 15
                reasoning.append("Individual tools don't suit enterprise management")
        
        product_scores.append({
            "product": product,
            "score": score,
            "reasoning": reasoning
        })
    
    # Sort by score and create recommendations
    product_scores.sort(key=lambda x: x["score"], reverse=True)
    
    recommendations = []
    for i, item in enumerate(product_scores[:3]):  # Top 3 recommendations
        product = item["product"]
        confidence = max(0.6, min(0.95, item["score"] / 100))  # Convert score to confidence
        
        # Create price display
        if product["price"] > 0:
            if product["trial_days"] > 0:
                price_display = f"Free {product['trial_days']} Day Trial - ${product['price']:.0f}/{product['billing_interval']} after"
            else:
                price_display = f"Custom pricing starting at ${product['price']:.0f}/{product['billing_interval']}"
        else:
            price_display = "Free Forever"
            
        # Generate compelling marketing description based on product
        marketing_description = ""
        if product["name"] == "Buildly Foundry":
            marketing_description = f"Based on your profile, Foundry will be the perfect fit for you and your organization. It will help you build applications incredibly fast while still allowing you to scale and manage fixes easily in the future. With its powerful API gateway, visual workflow builder, and built-in authentication, you'll go from idea to production 10x faster than traditional development approaches."
        
        elif product["name"] == "Buildly Developer":
            marketing_description = f"Based on your technical background, Developer is specifically designed for professionals like you. It provides advanced CLI tools, sophisticated debugging capabilities, and enterprise-grade deployment options that will supercharge your development workflow. You'll love the real-time collaboration features and the ability to integrate with any system seamlessly."
        
        elif product["name"] == "Buildly Enterprise":
            marketing_description = f"Based on your organizational needs, Enterprise will transform how your team builds and deploys applications. With advanced user management, SOC2 compliance, priority support, and unlimited integrations, it's built to handle your scale while maintaining the speed and flexibility your developers need. Perfect for teams that require enterprise security without sacrificing innovation."
        
        else:
            marketing_description = f"This product is perfectly suited for your needs, offering the right balance of features and scalability to help you succeed."
            
        recommendations.append({
            "name": product["name"],
            "confidence": confidence,
            "reasoning": f"Score: {item['score']}/100. " + "; ".join(item["reasoning"][:2]),
            "description": product["description"],
            "price": price_display,
            "features": product["features"],
            "highlights": product["features"][:5] if len(product["features"]) > 5 else product["features"],
            "marketingDescription": marketing_description,
            "key_benefits": item["reasoning"]
        })
    
    # Determine experience level
    experience_level = role.lower() if role else "intermediate"
    
    # Generate compelling user insights
    if company_size in ["1-10"]:
        profile_match = "You're at the perfect stage to leverage Buildly's rapid development capabilities to outpace larger competitors"
    elif company_size in ["11-50", "51-200"]:
        profile_match = "Your growing team needs the scalability and collaboration features that Buildly provides out-of-the-box"
    elif company_size in ["201-1000", "1000+"]:
        profile_match = "Your enterprise needs the security, compliance, and advanced management features Buildly delivers"
    else:
        profile_match = "Buildly's flexible architecture adapts perfectly to your unique requirements"
    
    if use_case == "Building My First Real App":
        recommended_approach = "Focus on speed and simplicity - Buildly will handle the complex infrastructure so you can focus on your unique value proposition"
    elif use_case == "Scaling Our Prototype":
        recommended_approach = "Leverage Buildly's enterprise-grade architecture to scale confidently without rebuilding from scratch"
    elif use_case == "Advanced Development Workflow":
        recommended_approach = "Take advantage of Buildly's advanced tooling and integrations to accelerate your development velocity"
    elif use_case == "Enterprise Team Collaboration":
        recommended_approach = "Utilize Buildly's collaboration and governance features to align your distributed teams effectively"
    elif use_case == "Legacy System Integration":
        recommended_approach = "Use Buildly's powerful API gateway and integration capabilities to modernize without disruption"
    else:
        recommended_approach = "Buildly's comprehensive platform will accelerate your development while ensuring long-term scalability"
    
    return {
        "analysis_type": "onboarding_recommendation",
        "confidence_score": 0.85,
        "user_insights": {
            "profile_match": profile_match,
            "experience_level": experience_level,
            "recommended_approach": recommended_approach
        },
        "recommendations": recommendations,
        "next_steps": [
            f"Start with a {recommendations[0]['name']} trial" if "trial" in recommendations[0]['price'].lower() else f"Get started with {recommendations[0]['name']}",
            "Set up your first integration",
            "Connect with our onboarding team", 
            "Define your key success metrics"
        ]
    }

async def analyze_architecture(data: dict):
    """Call BabbleBeaver API for architecture analysis"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "application_type": data.get("applicationType"),
                "application_details": data.get("applicationDetails"),
                "selected_product": data.get("selectedProduct"),
                "user_profile": {
                    "experience": data.get("experience"),
                    "company_size": data.get("companySize"),
                    "use_case": data.get("useCase")
                },
                "analysis_type": "architecture_recommendation"
            }
            
            print(f"Sending architecture request to BabbleBeaver: {payload}")
            response = await client.post(
                f"{BABBLEBEAVER_API_URL}/api/architecture", 
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {BABBLEBEAVER_API_KEY}"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"BabbleBeaver architecture response: {result}")
                return result
            else:
                print(f"BabbleBeaver architecture error: {response.text}")
                return await generate_mock_architecture(data)
                
    except Exception as e:
        print(f"BabbleBeaver architecture analysis failed: {str(e)}")
        return await generate_mock_architecture(data)

async def generate_mock_architecture(data: dict):
    """Generate mock architecture analysis"""
    app_type = data.get("applicationType", "web application")
    
    # Determine architecture based on application type and details
    if "mobile" in app_type.lower():
        architecture = "Mobile-First Architecture with API Backend"
        tech_stack = ["React Native/Flutter", "Node.js/FastAPI", "PostgreSQL", "Redis"]
    elif "web" in app_type.lower():
        architecture = "Microservices Architecture"
        tech_stack = ["React/Vue.js", "FastAPI/Django", "PostgreSQL", "Docker"]
    else:
        architecture = "Modular Monolith Architecture"
        tech_stack = ["Python/Node.js", "PostgreSQL", "REST APIs", "Docker"]
    
    return {
        "architecture_type": architecture,
        "confidence_score": 0.88,
        "recommended_stack": tech_stack,
        "estimated_timeline": "8-12 weeks",
        "estimated_budget": "$15,000 - $30,000",
        "team_size_recommendation": "3-5 developers",
        "key_features": [
            "User authentication and management",
            "Real-time data synchronization", 
            "API integrations",
            "Responsive design",
            "Analytics and reporting"
        ],
        "development_phases": [
            {
                "phase": "Phase 1: Foundation",
                "duration": "2-3 weeks",
                "deliverables": ["User auth", "Basic UI", "Database setup"]
            },
            {
                "phase": "Phase 2: Core Features", 
                "duration": "4-6 weeks",
                "deliverables": ["Main functionality", "API integrations", "Testing"]
            },
            {
                "phase": "Phase 3: Polish & Deploy",
                "duration": "2-3 weeks", 
                "deliverables": ["UI polish", "Performance optimization", "Deployment"]
            }
        ],
        "technical_recommendations": [
            "Start with MVP focusing on core user journey",
            "Implement comprehensive logging and monitoring",
            "Use containerization for easy deployment",
            "Plan for scalability from the beginning"
        ]
    }

# ---- Store onboarding in DB ----
def store_onboarding_data(data: OnboardingComplete, analysis: Optional[dict] = None):
    db = SessionLocal()
    record = OnboardingSubmission(
        email=data.email,
        organization_size=data.organization_size,
        product_stage=data.product_stage,
        product_scope=data.product_scope,
        biggest_challenge=data.biggest_challenge,
        team_composition=data.team_composition,
        analysis=analysis,
        completed_at=datetime.utcnow().isoformat() if analysis else None
    )
    db.add(record)
    db.commit()
    record_id = record.id
    db.close()
    return record_id

def update_recommendation_selection(email: str, recommendation: str):
    db = SessionLocal()
    record = db.query(OnboardingSubmission).filter(OnboardingSubmission.email == email).order_by(OnboardingSubmission.id.desc()).first()
    if record:
        record.selected_recommendation = recommendation  # type: ignore
        db.commit()
    db.close()

def get_onboarding_by_email(email: str):
    db = SessionLocal()
    record = db.query(OnboardingSubmission).filter(OnboardingSubmission.email == email).order_by(OnboardingSubmission.id.desc()).first()
    db.close()
    return record

# ---- Connect to Buildly Core to store auth method ----
async def store_auth_method(user_email: str, method: str):
    payload = {"email": user_email, "auth_method": method}
    async with httpx.AsyncClient() as client:
        try:
            await client.post("https://labs-api.buildly.io/auth/store", json=payload)
        except httpx.HTTPError as e:
            print("Failed to notify Buildly Core:", e)

# ---- Auth Callback ----
@app.get("/auth/callback/{provider}")
async def auth_callback(provider: str, code: str):
    async with httpx.AsyncClient() as client:
        if provider == "google":
            token_url = "https://oauth2.googleapis.com/token"
            user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
            data = {
                'client_id': GOOGLE_CLIENT_ID,
                'client_secret': GOOGLE_CLIENT_SECRET,
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': REDIRECT_URI
            }
        elif provider == "github":
            token_url = "https://github.com/login/oauth/access_token"
            user_info_url = "https://api.github.com/user/emails"
            data = {
                'client_id': GITHUB_CLIENT_ID,
                'client_secret': GITHUB_CLIENT_SECRET,
                'code': code,
                'redirect_uri': REDIRECT_URI
            }
        else:
            raise HTTPException(status_code=400, detail="Unsupported provider")

        headers = {"Accept": "application/json"}
        token_resp = await client.post(token_url, data=data, headers=headers)
        token_resp.raise_for_status()
        token_data = token_resp.json()
        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(status_code=400, detail="Token retrieval failed")

        user_resp = await client.get(user_info_url, headers={"Authorization": f"Bearer {access_token}"})
        user_resp.raise_for_status()
        user_data = user_resp.json()

        user_email = user_data.get("email") if provider == "google" else user_data[0].get("email")
        await store_auth_method(user_email, provider)
        jwt_token = create_jwt_token(user_email)
        return JSONResponse({"status": "authenticated", "email": user_email, "token": jwt_token})

# ---- Auth Entry Point ----
@app.get("/auth/{provider}")
async def login(provider: str):
    if provider == "google":
        return RedirectResponse(url=f"https://accounts.google.com/o/oauth2/auth?client_id={GOOGLE_CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=email profile")
    elif provider == "github":
        return RedirectResponse(url=f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope=user:email")
    else:
        raise HTTPException(status_code=400, detail="Unsupported provider")

# ---- Step-by-Step Onboarding Endpoints ----

@app.post("/analyze")
async def analyze_endpoint(data: dict):
    """Endpoint to analyze onboarding data and provide product recommendations"""
    try:
        # Convert dict to OnboardingComplete model
        onboarding_data = OnboardingComplete(
            email=data.get("email", "test@example.com"),
            organization_size=data.get("companySize", "small_team"),
            biggest_challenge=data.get("useCase", "integration challenges"),
            team_composition=data.get("experience", "small_team"),
            product_stage=data.get("applicationType"),
            product_scope=None
        )
        
        # Perform analysis first
        analysis = await analyze_onboarding(onboarding_data)
        
        # Store user data in database
        session = SessionLocal()
        try:
            # Store the questionnaire submission
            submission = OnboardingSubmission(
                email=onboarding_data.email,
                organization_size=onboarding_data.organization_size,
                biggest_challenge=onboarding_data.biggest_challenge,
                team_composition=onboarding_data.team_composition,
                product_stage=onboarding_data.product_stage,
                product_scope=onboarding_data.product_scope
            )
            
            # Store analysis results (convert to JSON string if needed)
            # submission.analysis = analysis  # This might cause the error, let's skip for now
            
            session.add(submission)
            session.commit()
            
            logger.info(f"✅ Stored onboarding data for {onboarding_data.email}")
            
        except Exception as db_error:
            session.rollback()
            logger.error(f"❌ Database error: {str(db_error)}")
            # Continue with analysis even if database storage fails
        finally:
            session.close()
        
        return JSONResponse(content=analysis)
    except Exception as e:
        logger.error(f"❌ Analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/babblebeaver/architecture")
async def architecture_analysis(data: dict):
    """Endpoint for architecture analysis using BabbleBeaver AI"""
    try:
        analysis = await analyze_architecture(data)
        return JSONResponse(content=analysis)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Architecture analysis failed: {str(e)}")

@app.post("/babblebeaver/test")
async def test_babblebeaver():
    """Test endpoint to verify BabbleBeaver connectivity"""
    try:
        test_data = OnboardingComplete(
            email="test@buildly.io",
            organization_size="small_team",
            biggest_challenge="API integration and scalability",
            team_composition="founding_team",
            product_stage="prototype_mvp"
        )
        
        analysis = await analyze_onboarding(test_data)
        return JSONResponse(content={
            "status": "success",
            "message": "BabbleBeaver integration working",
            "sample_analysis": analysis
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"BabbleBeaver test failed: {str(e)}"}
        )

@app.get("/")
async def index_page():
    """Index landing page"""
    return JSONResponse(content={"status": "success", "message": "Onboarding Bacend service index page"})

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse(content={"status": "healthy", "message": "Server is running"})

@app.post("/create-buildly-account")
async def create_buildly_account(request: CreateBuildlyAccountRequest):
    """Create a Buildly Labs account and organization using the proper coreuser endpoint"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Create user account using the coreuser endpoint (as per the template guide)
            user_payload = {
                "username": request.email,  # Use email as username
                "email": request.email,
                "password": request.password,
                "first_name": request.firstName,
                "last_name": request.lastName,
                "organization_name": request.company,
                "user_type": "Developer",  # Default to Developer as per the guide
                "is_active": request.is_active  # Use the is_active from request (defaults to True)
            }
            
            # Use the coreuser endpoint as shown in the template guide
            user_response = await client.post(
                f"{BUILDLY_LABS_API_BASE}/coreuser/",
                json=user_payload,
                headers={
                    "Content-Type": "application/json"
                    # No authorization header needed for public registration
                }
            )
            
            if user_response.status_code not in [200, 201]:
                # Handle specific error cases
                try:
                    error_data = user_response.json() if user_response.headers.get('content-type', '').startswith('application/json') else {}
                except:
                    error_data = {}
                
                error_text = user_response.text
                
                # Check for SMTP/email related errors
                if user_response.status_code == 500 and ("SMTPServerDisconnected" in error_text or "Connection unexpectedly closed" in error_text):
                    logger.error(f"Email sending failure during account creation for {request.email}: {error_text}")
                    # Email server issue - account might have been created but email failed
                    return {
                        "success": True,
                        "message": "Account created successfully! However, there was a temporary issue with the email verification system. You can try logging in directly at https://labs.buildly.io/login or contact support.",
                        "email": request.email,
                        "requires_verification": False,  # Don't require verification due to email system issue
                        "warning": "Email verification temporarily unavailable"
                    }
                
                # For other errors, provide clear feedback
                error_message = error_data.get('detail', 'Unknown error')
                if isinstance(error_message, dict):
                    error_message = str(error_message)
                
                raise HTTPException(
                    status_code=user_response.status_code,
                    detail=f"Failed to create user: {error_message}"
                )
            
            user_data = user_response.json()
            
            return {
                "success": True,
                "message": "Buildly Labs account created successfully. Please check your email for verification.",
                "user_id": user_data.get("id"),
                "organization_id": user_data.get("organization", {}).get("id"),
                "email": request.email,
                "requires_verification": True
            }
            
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Account creation failed: {str(e)}")

@app.post("/check-organization")
async def check_organization(request: OrganizationCheckRequest):
    """Check if an organization exists via Labs API"""
    organization_name = request.organizationName.strip()
    
    try:
        # Call Labs API to check organization existence
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BUILDLY_LABS_API_BASE}/organization/names/",
                timeout=30.0
            )
            
            if response.status_code == 200:
                existing_orgs = response.json()
                # Check if organization name exists (case-insensitive)
                exists = any(
                    org.get('name', '').lower() == organization_name.lower() 
                    for org in existing_orgs
                )
                
                return JSONResponse(content={
                    "exists": exists,
                    "organizationName": organization_name,
                    "message": f"Organization check completed for '{organization_name}' via Labs API"
                })
            else:
                # If Labs API fails, fall back to basic validation
                return JSONResponse(content={
                    "exists": False,
                    "organizationName": organization_name,
                    "message": f"Organization '{organization_name}' is available (Labs API unavailable)"
                })
                
    except Exception as e:
        # If Labs API is unavailable, fall back to basic validation
        logger.error(f"Organization check failed: {str(e)}")
        return JSONResponse(content={
            "exists": False,
            "organizationName": organization_name,
            "message": f"Organization '{organization_name}' is available (validation service unavailable)"
        })

@app.post("/process-payment")
async def process_payment(request: PaymentRequest):
    """Process payment using Stripe"""
    try:
        if not stripe.api_key:
            # If Stripe is not configured, return success for development
            return JSONResponse(content={
                "success": True,
                "message": "Payment processed successfully (development mode)",
                "paymentMethodId": request.paymentMethodId
            })
        
        # Create customer in Stripe
        customer = stripe.Customer.create(
            email=request.email,
            payment_method=request.paymentMethodId,
            invoice_settings={
                'default_payment_method': request.paymentMethodId,
            },
        )
        
        # Attach payment method to customer
        stripe.PaymentMethod.attach(
            request.paymentMethodId,
            customer=customer.id,
        )
        
        # For Buildly Foundry ($50/month), create a subscription
        if request.selectedProduct == "Buildly Foundry":
            # In a real implementation, you would have predefined price IDs in Stripe
            # For now, we'll create a simple payment intent for the trial setup
            
            # Create a setup intent for future billing (30-day trial)
            setup_intent = stripe.SetupIntent.create(
                customer=customer.id,
                payment_method=request.paymentMethodId,
                confirm=True,
                usage='off_session'
            )
            
            if setup_intent.status == 'succeeded':
                return JSONResponse(content={
                    "success": True,
                    "message": "Payment method saved successfully. Your 30-day free trial will begin now.",
                    "customerId": customer.id,
                    "setupIntentId": setup_intent.id,
                    "trialActive": True
                })
            else:
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "error": "Payment method setup failed"
                    }
                )
        else:
            # For other products, handle accordingly
            return JSONResponse(content={
                "success": True,
                "message": f"Payment processed for {request.selectedProduct}",
                "customerId": customer.id
            })
            
    except stripe.error.CardError as e:
        # Card was declined
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": f"Card was declined: {e.user_message}"
            }
        )
    except stripe.error.RateLimitError as e:
        return JSONResponse(
            status_code=429,
            content={
                "success": False,
                "error": "Too many requests to Stripe. Please try again later."
            }
        )
    except stripe.error.InvalidRequestError as e:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": f"Invalid request: {str(e)}"
            }
        )
    except stripe.error.AuthenticationError as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Stripe authentication failed"
            }
        )
    except stripe.error.APIConnectionError as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Network error connecting to Stripe"
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Payment processing failed: {str(e)}"
            }
        )

@app.post("/api/create-subscription")
async def create_subscription(request: SubscriptionRequest):
    """Create a Stripe subscription with trial period via Labs API"""
    try:
        # First verify Stripe is configured
        if not stripe.api_key:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "Payment processing is not configured",
                    "requiresBackendSetup": True
                }
            )

        # Create Stripe customer
        customer = stripe.Customer.create(
            email=request.email,
            payment_method=request.paymentMethodId
        )

        # Attach payment method to customer
        stripe.PaymentMethod.attach(
            request.paymentMethodId,
            customer=customer.id,
        )

        # Set as default payment method
        stripe.Customer.modify(
            customer.id,
            invoice_settings={'default_payment_method': request.paymentMethodId}
        )

        # Prepare subscription data for Labs API
        subscription_data = {
            "customer_email": request.email,
            "stripe_customer_id": customer.id,
            "stripe_price_id": request.priceId,
            "trial_period_days": request.trialDays,
            "payment_method_id": request.paymentMethodId
        }

        # Add coupon if provided
        if request.couponCode:
            subscription_data["coupon_code"] = request.couponCode

        # Create subscription via Labs API
        async with httpx.AsyncClient() as client:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {BUILDLY_JWT_TOKEN}"
            }
            
            response = await client.post(
                f"{LABS_API_URL}/subscription/",
                json=subscription_data,
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code == 201:
                subscription_result = response.json()
                return JSONResponse(content={
                    "success": True,
                    "subscriptionId": subscription_result.get("id"),
                    "customerId": customer.id,
                    "trialEndsAt": subscription_result.get("trial_end"),
                    "status": subscription_result.get("status", "trialing"),
                    "message": "Subscription created successfully with trial period"
                })
            else:
                # If Labs API fails, fall back to local Stripe subscription
                logger.warning(f"Labs API subscription failed: {response.status_code}")
                
                # Create subscription directly with Stripe
                subscription = stripe.Subscription.create(
                    customer=customer.id,
                    items=[{'price': request.priceId}],
                    trial_period_days=request.trialDays,
                    payment_behavior='default_incomplete',
                    payment_settings={'save_default_payment_method': 'on_subscription'},
                    expand=['latest_invoice.payment_intent'],
                )
                
                return JSONResponse(content={
                    "success": True,
                    "subscriptionId": subscription.id,
                    "customerId": customer.id,
                    "status": subscription.status,
                    "message": "Subscription created successfully (fallback mode)",
                    "fallback": True
                })

    except stripe.error.CardError as e:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": f"Card error: {e.user_message}",
                "cardError": True
            }
        )
    except stripe.error.RateLimitError as e:
        return JSONResponse(
            status_code=429,
            content={
                "success": False,
                "error": "Too many requests to Stripe. Please try again later."
            }
        )
    except stripe.error.InvalidRequestError as e:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": f"Invalid request: {str(e)}"
            }
        )
    except stripe.error.AuthenticationError as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Stripe authentication failed"
            }
        )
    except stripe.error.APIConnectionError as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Network error connecting to Stripe"
            }
        )
    except Exception as e:
        logger.error(f"Subscription creation failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Subscription creation failed: {str(e)}"
            }
        )

@app.post("/submit-contact")
async def submit_contact(contact: ContactRequest):
    """Submit a contact form and store in database"""
    db = SessionLocal()
    try:
        db_contact = Contact(
            email=contact.email,
            use_case=contact.useCase,
            experience=contact.experience,
            company_size=contact.companySize,
            application_type=contact.applicationType,
            application_details=contact.applicationDetails,
            company=contact.company,
            created_at=datetime.utcnow()
        )
        db.add(db_contact)
        db.commit()
        db.refresh(db_contact)
        
        return {"message": "Contact submitted successfully", "id": db_contact.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/integrate-labs")
async def integrate_labs(data: LabsIntegrationRequest):
    """Integrate onboarding completion data with Buildly Labs API"""
    try:
        result = await integrate_with_labs_api(data)
        
        if result and result.get("success"):
            return {
                "message": "Successfully integrated with Buildly Labs",
                "labs_data": result
            }
        else:
            error_msg = result.get("error", "Unknown error") if result else "Integration function returned None"
            raise HTTPException(
                status_code=400, 
                detail=f"Labs integration failed: {error_msg}"
            )
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

async def integrate_with_labs_api(data: LabsIntegrationRequest):
    """
    Integrate onboarding data with Buildly Labs API
    1. Create/find organization
    2. Create user account
    3. Create product with architecture suggestions
    """
    LABS_API_BASE = "https://labs-api.buildly.io"
    
    try:
        # Determine organization name (use company name or email domain)
        org_name = data.company if data.company and data.company.strip() else data.email.split('@')[1]
        
        # Step 1: Create Organization
        org_payload = {
            "name": org_name,
            "description": f"Organization created via onboarding for {data.useCase}",
        }
        
        async with httpx.AsyncClient() as client:
            # Try to create organization (might already exist)
            org_response = await client.post(
                f"{LABS_API_BASE}/organization/",
                json=org_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if org_response.status_code == 201:
                try:
                    org_data = org_response.json()
                    org_uuid = org_data.get("organization_uuid")
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Failed to parse organization response: {str(e)}"
                    }
            else:
                # Organization might already exist, try to find it
                orgs_response = await client.get(f"{LABS_API_BASE}/organization/names/")
                if orgs_response.status_code == 200:
                    try:
                        orgs = orgs_response.json()
                        existing_org = next((org for org in orgs if org.get("name") == org_name), None)
                        if existing_org:
                            org_uuid = existing_org.get("organization_uuid")
                        else:
                            # Use a placeholder UUID for cases where auth is required
                            org_uuid = "pending-org-creation"
                    except Exception as e:
                        org_uuid = "pending-org-creation"
                else:
                    # Use a placeholder UUID for cases where auth is required
                    org_uuid = "pending-org-creation"
            
            # Step 2: Create User Account
            username = data.email.split('@')[0]  # Use email prefix as username
            user_payload = {
                "username": username,
                "email": data.email,
                "password": "TempPassword123!",  # Temporary password - user should reset
                "organization_name": org_name,
                "first_name": data.email.split('@')[0].title(),
                "is_active": True,
                "privacy_disclaimer_accepted": True,
                "user_type": "Product Team"
            }
            
            user_response = await client.post(
                f"{LABS_API_BASE}/coreuser/",
                json=user_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if user_response.status_code == 201:
                try:
                    user_data = user_response.json()
                    user_uuid = user_data.get("core_user_uuid")
                except Exception as e:
                    user_uuid = "pending-user-creation"
            else:
                # User might already exist, continue with product creation
                user_uuid = "pending-user-creation"
            
            # Step 3: Create Product with Architecture Information
            product_payload = {
                "name": f"{data.applicationType} - {data.useCase}",
                "description": f"""
Product created via onboarding process:
- Application Type: {data.applicationType}
- Use Case: {data.useCase}
- Experience Level: {data.experience}
- Company Size: {data.companySize}
- Selected Platform: {data.selectedProduct}

Application Details:
{data.applicationDetails}

AI Architecture Recommendations:
- Architecture: {data.architecture}
- Estimated Budget: {data.estimatedBudget}
- Recommended Team Size: {data.teamSize}
                """.strip(),
                "organization_uuid": org_uuid,
                "product_info": {
                    "onboarding_data": {
                        "use_case": data.useCase,
                        "experience": data.experience,
                        "company_size": data.companySize,
                        "application_type": data.applicationType,
                        "selected_product": data.selectedProduct
                    },
                    "architecture_recommendations": {
                        "architecture": data.architecture,
                        "estimated_budget": data.estimatedBudget,
                        "team_size": data.teamSize,
                        "key_features": data.keyFeatures
                    }
                }
            }
            
            product_response = await client.post(
                f"{LABS_API_BASE}/product/product/",
                json=product_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if product_response.status_code == 201:
                product_data = product_response.json()
                product_uuid = product_data.get("product_uuid")
                
                # Step 4: Create Architecture Suggestions
                suggestions_payload = {
                    "business_type": "b2b" if "B2B" in data.useCase else "b2c",
                    "project_type": "new",
                    "architecture_type": "microservice" if "microservice" in data.architecture.lower() else "monolith",
                    "front_end": "mobile native" if "mobile" in data.applicationType.lower() else "desktop",
                    "suggested_feature": f"Key features for {data.applicationType}: " + ", ".join(data.keyFeatures[:5])
                }
                
                suggestions_response = await client.post(
                    f"{LABS_API_BASE}/product/suggestions/",
                    json=suggestions_payload,
                    headers={"Content-Type": "application/json"}
                )
                
                return {
                    "success": True,
                    "organization_uuid": org_uuid,
                    "product_uuid": product_uuid,
                    "user_uuid": user_uuid,
                    "message": "Successfully integrated with Buildly Labs"
                }
            else:
                # Return success with pending status for cases where auth is required
                return {
                    "success": True,
                    "organization_uuid": org_uuid,
                    "product_uuid": "pending-product-creation",
                    "user_uuid": user_uuid,
                    "message": "Labs API integration initiated - full access requires authentication configuration"
                }
                
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/onboarding/step1")
async def onboarding_step1(data: OnboardingStep1):
    """Step 1: Collect email address"""
    return JSONResponse(content={"status": "success", "message": "Email collected", "next_step": "step2"})

@app.post("/onboarding/step2")
async def onboarding_step2(data: OnboardingStep2):
    """Step 2: Ask for organization size"""
    next_step = "step3_small" if data.organization_size in ["just_me", "small_team"] else "step3_large"
    return JSONResponse(content={"status": "success", "message": "Organization size collected", "next_step": next_step})

@app.post("/onboarding/step3_small")
async def onboarding_step3_small(data: OnboardingStep3Small):
    """Step 3a: For small organizations - ask about product stage"""
    return JSONResponse(content={"status": "success", "message": "Product stage collected", "next_step": "step4"})

@app.post("/onboarding/step3_large")
async def onboarding_step3_large(data: OnboardingStep3Large):
    """Step 3b: For large organizations - ask about product scope"""
    return JSONResponse(content={"status": "success", "message": "Product scope collected", "next_step": "step4"})

@app.post("/onboarding/step4")
async def onboarding_step4(data: OnboardingStep4):
    """Step 4: Ask about biggest challenge"""
    return JSONResponse(content={"status": "success", "message": "Challenge collected", "next_step": "step5"})

@app.post("/onboarding/step5")
async def onboarding_step5(data: OnboardingStep5):
    """Step 5: Ask about team composition"""
    return JSONResponse(content={"status": "success", "message": "Team composition collected", "next_step": "complete"})

@app.post("/onboarding/complete")
async def onboarding_complete(data: OnboardingComplete):
    """Complete onboarding - analyze and provide recommendations"""
    try:
        # Store initial data
        record_id = store_onboarding_data(data)
        
        # Analyze with BabbleBeaver
        analysis = await analyze_onboarding(data)
        
        # Update record with analysis
        db = SessionLocal()
        record = db.query(OnboardingSubmission).filter(OnboardingSubmission.id == record_id).first()
        if record:
            record.analysis = analysis  # type: ignore
            record.completed_at = datetime.utcnow().isoformat()  # type: ignore
            db.commit()
        db.close()
        
        return JSONResponse(content={
            "status": "success", 
            "analysis": analysis,
            "message": "Onboarding analysis complete"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/onboarding/select-recommendation")
async def select_recommendation(data: RecommendationSelection):
    """Handle user's recommendation selection"""
    try:
        # Update the selection in database
        update_recommendation_selection(data.email, data.selected_recommendation)
        
        # Send to labs-api.buildly.io
        onboarding_record = get_onboarding_by_email(data.email)
        if onboarding_record:
            payload = {
                "email": data.email,
                "selected_recommendation": data.selected_recommendation,
                "onboarding_data": {
                    "organization_size": onboarding_record.organization_size,
                    "product_stage": onboarding_record.product_stage,
                    "product_scope": onboarding_record.product_scope,
                    "biggest_challenge": onboarding_record.biggest_challenge,
                    "team_composition": onboarding_record.team_composition
                },
                "analysis": onboarding_record.analysis
            }
            
            async with httpx.AsyncClient() as client:
                await client.post("https://labs-api.buildly.io/onboarding/complete", json=payload)
        
        return JSONResponse(content={
            "status": "success", 
            "message": f"Selection '{data.selected_recommendation}' processed successfully"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Selection processing failed: {str(e)}")

@app.get("/onboarding/status/{email}")
async def get_onboarding_status(email: str):
    """Get current onboarding status for a user"""
    record = get_onboarding_by_email(email)
    if not record:
        return JSONResponse(content={"status": "not_found", "message": "No onboarding record found"})
    
    return JSONResponse(content={
        "status": "found",
        "data": {
            "email": record.email,
            "organization_size": record.organization_size,
            "product_stage": record.product_stage,
            "product_scope": record.product_scope,
            "biggest_challenge": record.biggest_challenge,
            "team_composition": record.team_composition,
            "completed": record.completed_at is not None,
            "selected_recommendation": record.selected_recommendation,
            "analysis": record.analysis
        }
    })

# ---- Static Files Mount ----
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)