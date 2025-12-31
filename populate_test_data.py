"""
Script to populate test data for admin panel testing
This will create sample content for all content types to test the admin forms
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timedelta
import random

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent))

from app.db.database import get_db_session
from app.models.content import Content, ContentTypeEnum, ContentStatusEnum
from app.models.category import Category
from app.models.media import Media
from app.models.myth_fact import MythFact
from app.models.user import User


async def create_categories():
    """Create sample categories or get existing ones"""
    from sqlalchemy import select
    
    async with get_db_session() as db:
        # Check if categories already exist
        result = await db.execute(select(Category))
        existing_categories = result.scalars().all()
        
        if existing_categories:
            print(f"Found {len(existing_categories)} existing categories")
            return existing_categories
        
        # Create new categories if none exist
        categories_data = [
            {
                "name": "Wildlife Conservation",
                "slug": "wildlife-conservation",
                "description": "Articles and resources about protecting wildlife and their habitats",
                "is_active": True
            },
            {
                "name": "Marine Life",
                "slug": "marine-life", 
                "description": "Content focused on ocean and marine ecosystem conservation",
                "is_active": True
            },
            {
                "name": "Forest Protection",
                "slug": "forest-protection",
                "description": "Information about forest conservation and sustainable practices",
                "is_active": True
            },
            {
                "name": "Endangered Species",
                "slug": "endangered-species",
                "description": "Focus on protecting endangered and threatened species",
                "is_active": True
            },
            {
                "name": "Climate Change",
                "slug": "climate-change",
                "description": "Climate change impact on wildlife and ecosystems",
                "is_active": True
            }
        ]
        
        created_categories = []
        for cat_data in categories_data:
            category = Category(**cat_data)
            db.add(category)
            created_categories.append(category)
        
        await db.commit()
        
        # Refresh to get IDs
        for category in created_categories:
            await db.refresh(category)
        
        return created_categories


async def create_blog_posts(categories, author_id):
    """Create sample blog posts"""
    
    blog_posts = [
        {
            "title": "The Majestic Tigers of Sundarbans: A Conservation Success Story",
            "content": """<h2>Introduction</h2>
<p>The Sundarbans mangrove forests, spanning across Bangladesh and India, represent one of the world's most unique ecosystems. Home to the legendary Bengal tigers, this UNESCO World Heritage site has become a beacon of hope for wildlife conservation efforts worldwide.</p>

<h2>The Challenge</h2>
<p>For decades, the Bengal tiger population in the Sundarbans faced numerous threats:</p>
<ul>
<li>Habitat loss due to human encroachment</li>
<li>Climate change and rising sea levels</li>
<li>Human-wildlife conflict</li>
<li>Illegal poaching and wildlife trafficking</li>
</ul>

<h2>Conservation Efforts</h2>
<p>Through collaborative efforts between local communities, government agencies, and international conservation organizations, several key initiatives have been implemented:</p>

<h3>Community-Based Conservation</h3>
<p>Local fishing communities have been trained as forest guards and wildlife monitors, creating a network of grassroots conservationists who understand the importance of protecting their natural heritage.</p>

<h3>Technology Integration</h3>
<p>Advanced camera traps, GPS tracking, and drone surveillance have revolutionized monitoring efforts, providing real-time data on tiger movements and population dynamics.</p>

<h2>Results and Impact</h2>
<p>The latest census data shows a remarkable 30% increase in tiger population over the past decade. This success story demonstrates that with proper planning, community involvement, and sustained effort, we can reverse the decline of endangered species.</p>

<h2>Future Outlook</h2>
<p>While celebrating these achievements, we must remain vigilant. Climate change continues to pose significant challenges, and ongoing support is crucial for maintaining these conservation gains.</p>""",
            "excerpt": "Discover how the Sundarbans mangrove forests became a conservation success story, with Bengal tiger populations increasing by 30% through community involvement and innovative technology.",
            "author_name": "Dr. Sarah Mitchell",
            "featured_image": "/uploads/images/sundarbans-tiger.jpg",
            "slug": "sundarbans-tigers-conservation-success",
            "content_metadata": {"tags": ["tigers", "sundarbans", "conservation", "success-story"]},
            "type": ContentTypeEnum.BLOG,
            "status": ContentStatusEnum.PUBLISHED,
            "author_id": author_id
        },
        {
            "title": "Ocean Plastic: The Silent Killer of Marine Wildlife",
            "content": """<h2>The Plastic Crisis</h2>
<p>Every minute, the equivalent of a garbage truck full of plastic enters our oceans. This staggering statistic represents one of the most pressing environmental challenges of our time, with devastating consequences for marine life.</p>

<h2>Impact on Marine Species</h2>
<p>Plastic pollution affects marine life in multiple ways:</p>

<h3>Entanglement</h3>
<p>Sea turtles, seals, and whales often become entangled in plastic debris, leading to injury, infection, and death. Ghost fishing nets, abandoned by commercial fishing operations, continue to trap and kill marine animals for decades.</p>

<h3>Ingestion</h3>
<p>Marine animals mistake plastic fragments for food, leading to internal injuries, starvation, and toxic chemical exposure. Recent studies have found microplastics in the stomachs of fish, seabirds, and even plankton.</p>

<h2>Solutions and Action</h2>
<p>Addressing the plastic crisis requires coordinated global action:</p>

<ul>
<li><strong>Reduce Single-Use Plastics:</strong> Supporting legislation to ban or reduce single-use plastic items</li>
<li><strong>Improve Recycling:</strong> Investing in better recycling infrastructure and technology</li>
<li><strong>Ocean Cleanup:</strong> Supporting organizations working to remove plastic from our oceans</li>
<li><strong>Education:</strong> Raising awareness about plastic pollution and its impacts</li>
</ul>

<h2>What You Can Do</h2>
<p>Individual actions, when multiplied across millions of people, can make a significant difference:</p>
<ul>
<li>Use reusable bags, bottles, and containers</li>
<li>Participate in beach cleanups</li>
<li>Support businesses that use sustainable packaging</li>
<li>Advocate for policy changes in your community</li>
</ul>""",
            "excerpt": "Explore the devastating impact of plastic pollution on marine wildlife and discover actionable solutions to protect our oceans and the creatures that call them home.",
            "author_name": "Dr. Maria Rodriguez",
            "featured_image": "/uploads/images/ocean-plastic-pollution.jpg",
            "slug": "ocean-plastic-marine-wildlife-crisis",
            "tags": ["ocean", "plastic", "pollution", "marine-life"],
            "type": ContentTypeEnum.BLOG,
            "status": ContentStatusEnum.PUBLISHED
        },
        {
            "title": "Rewilding Europe: Bringing Back the Wild",
            "content": """<h2>The Rewilding Movement</h2>
<p>Across Europe, an ambitious conservation movement is gaining momentum. Rewilding - the process of restoring natural ecosystems and reintroducing native species - is transforming landscapes and bringing back biodiversity to regions where it had been lost.</p>

<h2>Success Stories</h2>

<h3>Yellowstone Wolves Effect</h3>
<p>The reintroduction of wolves to Yellowstone National Park in the 1990s created a cascade of ecological benefits, demonstrating the power of apex predators in maintaining ecosystem balance.</p>

<h3>European Bison Return</h3>
<p>Once extinct in the wild, European bison have been successfully reintroduced to several European countries, including Romania, Poland, and the Netherlands.</p>

<h2>Challenges and Solutions</h2>
<p>Rewilding projects face several challenges:</p>
<ul>
<li>Human-wildlife conflict</li>
<li>Agricultural concerns</li>
<li>Economic considerations</li>
<li>Political and social acceptance</li>
</ul>

<p>Successful rewilding requires:</p>
<ul>
<li>Community engagement and education</li>
<li>Compensation schemes for farmers</li>
<li>Gradual implementation</li>
<li>Continuous monitoring and adaptation</li>
</ul>

<h2>The Future of Rewilding</h2>
<p>As climate change accelerates and biodiversity loss continues, rewilding offers hope for ecosystem restoration. By working with natural processes rather than against them, we can create resilient landscapes that benefit both wildlife and human communities.</p>""",
            "excerpt": "Discover how rewilding projects across Europe are restoring natural ecosystems and bringing back native species, creating hope for biodiversity recovery.",
            "author_name": "Prof. James Thompson",
            "featured_image": "/uploads/images/european-rewilding.jpg",
            "slug": "rewilding-europe-bringing-back-wild",
            "tags": ["rewilding", "europe", "biodiversity", "restoration"],
            "type": ContentTypeEnum.BLOG,
            "status": ContentStatusEnum.DRAFT
        }
    ]
    
    async with get_db_session() as db:
        for i, post_data in enumerate(blog_posts):
            category = random.choice(categories)
            
            # Clean up the data and add required fields
            clean_data = {
                "title": post_data["title"],
                "content": post_data["content"],
                "excerpt": post_data.get("excerpt", ""),
                "author_name": post_data.get("author_name", "Admin"),
                "featured_image": post_data.get("featured_image"),
                "slug": post_data.get("slug"),
                "type": post_data["type"],
                "status": post_data["status"],
                "author_id": author_id,
                "category_id": category.id,
                "content_metadata": {"tags": post_data.get("tags", [])}
            }
            
            blog_post = Content(**clean_data)
            db.add(blog_post)
        
        await db.commit()


async def create_case_studies(categories):
    """Create sample case studies"""
    from uuid import uuid4
    
    # Create a dummy user ID for content
    dummy_author_id = uuid4()
    
    case_studies = [
        {
            "title": "Saving the Amur Leopard: A Collaborative Conservation Effort",
            "content": """<h2>Executive Summary</h2>
<p>The Amur leopard (Panthera pardus orientalis) is one of the world's most endangered big cats, with fewer than 200 individuals remaining in the wild. This case study examines the comprehensive conservation program that has helped stabilize and slowly increase the population through international collaboration, habitat protection, and anti-poaching measures.</p>

<h2>Background</h2>
<p>Once widespread across northeastern China, eastern Russia, and the Korean Peninsula, the Amur leopard's range has been reduced by over 95%. By 2007, estimates suggested fewer than 30 individuals remained in the wild.</p>

<h2>Key Challenges</h2>
<ul>
<li><strong>Habitat Fragmentation:</strong> Agricultural expansion and urban development fragmented remaining forest habitats</li>
<li><strong>Poaching:</strong> Demand for leopard pelts and bones in illegal wildlife trade</li>
<li><strong>Prey Depletion:</strong> Overhunting of deer and wild boar reduced available prey</li>
<li><strong>Human-Wildlife Conflict:</strong> Leopards occasionally preyed on domestic animals</li>
<li><strong>Inbreeding:</strong> Small population size led to reduced genetic diversity</li>
</ul>

<h2>Conservation Strategy</h2>

<h3>Habitat Protection</h3>
<p>Establishment of the Land of the Leopard National Park in Russia (2012) and improved protection of existing reserves created a network of protected areas covering over 650,000 hectares.</p>

<h3>Anti-Poaching Measures</h3>
<ul>
<li>Increased ranger patrols with modern equipment</li>
<li>Camera trap networks for monitoring</li>
<li>Collaboration with law enforcement agencies</li>
<li>Community education programs</li>
</ul>

<h3>Prey Recovery</h3>
<p>Hunting restrictions and habitat restoration led to recovery of prey species, particularly red deer and wild boar populations.</p>

<h3>International Collaboration</h3>
<p>Partnership between Russian, Chinese, and international conservation organizations ensured coordinated cross-border conservation efforts.</p>

<h2>Results and Outcomes</h2>
<p>Recent surveys indicate the Amur leopard population has increased to approximately 180-200 individuals, representing a significant recovery from the critically low numbers of the early 2000s.</p>

<h3>Key Achievements</h3>
<ul>
<li>Population increase of over 500% since 2007</li>
<li>Establishment of protected corridor connecting Russian and Chinese habitats</li>
<li>Successful breeding programs in captivity as genetic backup</li>
<li>Reduced human-wildlife conflict through compensation schemes</li>
<li>Increased local community support for conservation</li>
</ul>

<h2>Lessons Learned</h2>
<ul>
<li>International cooperation is essential for transboundary species conservation</li>
<li>Long-term commitment and sustained funding are crucial</li>
<li>Community engagement and economic incentives improve conservation outcomes</li>
<li>Technology (camera traps, GPS collars) enhances monitoring effectiveness</li>
<li>Habitat protection must address entire ecosystem needs</li>
</ul>

<h2>Future Outlook</h2>
<p>While the Amur leopard remains critically endangered, this case demonstrates that dedicated conservation efforts can reverse species decline. Continued support for habitat protection, anti-poaching measures, and international cooperation will be essential for long-term recovery.</p>

<h2>Recommendations</h2>
<ul>
<li>Expand protected area networks</li>
<li>Strengthen cross-border cooperation</li>
<li>Develop sustainable ecotourism opportunities</li>
<li>Continue genetic monitoring and management</li>
<li>Invest in local community development programs</li>
</ul>""",
            "excerpt": "An in-depth analysis of the successful conservation program that helped increase the critically endangered Amur leopard population from fewer than 30 to nearly 200 individuals through international collaboration and comprehensive habitat protection.",
            "author_name": "Dr. Elena Volkov",
            "featured_image": "/uploads/images/amur-leopard-case-study.jpg",
            "slug": "amur-leopard-conservation-case-study",
            "tags": ["amur-leopard", "case-study", "conservation", "endangered-species"],
            "type": ContentTypeEnum.CASE_STUDY,
            "status": ContentStatusEnum.PUBLISHED
        },
        {
            "title": "Coral Reef Restoration in the Maldives: Innovation Meets Tradition",
            "content": """<h2>Project Overview</h2>
<p>The Maldives Coral Restoration Project represents one of the most innovative approaches to coral reef conservation in the Indian Ocean. Combining cutting-edge marine science with traditional Maldivian knowledge, this initiative has successfully restored over 50 hectares of degraded reef systems.</p>

<h2>The Challenge</h2>
<p>The Maldives, consisting of 1,192 coral islands, depends entirely on healthy coral reefs for:</p>
<ul>
<li>Coastal protection from storm surges and erosion</li>
<li>Tourism revenue (90% of the economy)</li>
<li>Fisheries and food security</li>
<li>Cultural and spiritual significance</li>
</ul>

<p>Climate change, particularly rising sea temperatures and ocean acidification, has caused widespread coral bleaching events, with some reefs experiencing 90% mortality rates.</p>

<h2>Methodology</h2>

<h3>Site Selection</h3>
<p>Restoration sites were selected based on:</p>
<ul>
<li>Historical reef health data</li>
<li>Current environmental conditions</li>
<li>Community priorities and needs</li>
<li>Accessibility for monitoring</li>
</ul>

<h3>Coral Propagation Techniques</h3>
<p>The project employed multiple restoration methods:</p>

<h4>Coral Nurseries</h4>
<p>Floating and fixed nursery structures were established to grow coral fragments in optimal conditions before transplantation to degraded reef areas.</p>

<h4>Micro-fragmentation</h4>
<p>Coral colonies were carefully fragmented to stimulate faster growth rates, reducing restoration timelines from decades to years.</p>

<h4>Fusion Technology</h4>
<p>Coral fragments were fused together to create larger, more resilient colonies capable of surviving environmental stresses.</p>

<h3>Community Involvement</h3>
<p>Local communities were integral to project success:</p>
<ul>
<li>Traditional fishers became coral gardeners</li>
<li>Women's groups managed nursery maintenance</li>
<li>Youth participated in monitoring programs</li>
<li>Elders shared traditional ecological knowledge</li>
</ul>

<h2>Results and Impact</h2>

<h3>Ecological Outcomes</h3>
<ul>
<li>50+ hectares of reef restored</li>
<li>75% survival rate of transplanted corals</li>
<li>40% increase in fish abundance on restored reefs</li>
<li>Recovery of key species including grouper and parrotfish</li>
<li>Improved reef structural complexity</li>
</ul>

<h3>Socio-Economic Benefits</h3>
<ul>
<li>Creation of 150 green jobs</li>
<li>Increased tourism revenue for participating communities</li>
<li>Enhanced food security through improved fisheries</li>
<li>Strengthened cultural connections to marine environment</li>
</ul>

<h2>Challenges and Adaptations</h2>

<h3>Environmental Challenges</h3>
<ul>
<li>Recurring bleaching events required heat-resistant coral selection</li>
<li>Monsoon seasons disrupted nursery operations</li>
<li>Crown-of-thorns starfish outbreaks threatened restored areas</li>
</ul>

<h3>Adaptive Management</h3>
<ul>
<li>Development of climate-resilient coral strains</li>
<li>Seasonal adjustment of restoration activities</li>
<li>Integrated pest management strategies</li>
<li>Continuous monitoring and adaptive protocols</li>
</ul>

<h2>Innovation Highlights</h2>

<h3>Technology Integration</h3>
<ul>
<li>Underwater drones for monitoring</li>
<li>3D printing of reef structures</li>
<li>AI-powered coral health assessment</li>
<li>Mobile apps for community data collection</li>
</ul>

<h3>Traditional Knowledge Integration</h3>
<ul>
<li>Seasonal timing based on lunar cycles</li>
<li>Species selection guided by local expertise</li>
<li>Traditional management practices adapted for restoration</li>
<li>Community-based monitoring systems</li>
</ul>

<h2>Lessons Learned</h2>
<ul>
<li>Community ownership is essential for long-term success</li>
<li>Combining multiple restoration techniques improves outcomes</li>
<li>Climate resilience must be built into restoration planning</li>
<li>Traditional knowledge enhances scientific approaches</li>
<li>Continuous monitoring enables adaptive management</li>
</ul>

<h2>Scaling and Replication</h2>
<p>The success of this project has led to replication efforts across the Indian Ocean region, with adaptation to local conditions and communities.</p>

<h3>Regional Expansion</h3>
<ul>
<li>Similar projects initiated in Seychelles and Mauritius</li>
<li>Training programs for other island nations</li>
<li>Knowledge sharing through regional networks</li>
<li>Development of standardized protocols</li>
</ul>

<h2>Future Directions</h2>
<ul>
<li>Expansion to 100+ hectares by 2025</li>
<li>Development of coral probiotics for disease resistance</li>
<li>Integration with blue carbon initiatives</li>
<li>Enhanced climate monitoring and early warning systems</li>
</ul>""",
            "excerpt": "Explore how the Maldives successfully restored over 50 hectares of coral reefs by combining innovative marine science with traditional knowledge, creating a model for reef restoration worldwide.",
            "author_name": "Dr. Ahmed Hassan",
            "featured_image": "/uploads/images/maldives-coral-restoration.jpg",
            "slug": "maldives-coral-restoration-innovation",
            "tags": ["coral-reef", "maldives", "restoration", "marine-conservation"],
            "type": ContentTypeEnum.CASE_STUDY,
            "status": ContentStatusEnum.PUBLISHED
        }
    ]
    
    async with get_db_session() as db:
        for i, study_data in enumerate(case_studies):
            category = random.choice(categories)
            study_data["category_id"] = category.id
            study_data["author_id"] = dummy_author_id
            
            # Convert tags to metadata if present
            if "tags" in study_data:
                study_data["content_metadata"] = {"tags": study_data.pop("tags")}
            
            case_study = Content(**study_data)
            db.add(case_study)
        
        await db.commit()


async def create_conservation_efforts(categories):
    """Create sample conservation efforts"""
    from uuid import uuid4
    dummy_author_id = uuid4()
    
    conservation_efforts = [
        {
            "title": "Project Elephant Corridor: Connecting Fragmented Habitats",
            "content": """<h2>Project Overview</h2>
<p>Project Elephant Corridor is an ambitious conservation initiative aimed at creating safe passage routes for Asian elephants across fragmented landscapes in Southeast Asia. By establishing wildlife corridors, the project addresses one of the most critical threats to elephant survival: habitat fragmentation.</p>

<h2>The Problem</h2>
<p>Asian elephant populations have declined by over 50% in the past three generations due to:</p>
<ul>
<li>Rapid urbanization and agricultural expansion</li>
<li>Infrastructure development (roads, railways, dams)</li>
<li>Human-elephant conflict</li>
<li>Loss of traditional migration routes</li>
</ul>

<h2>Our Solution</h2>

<h3>Corridor Identification</h3>
<p>Using GPS tracking data from collared elephants, satellite imagery, and local knowledge, we identified critical movement pathways between protected areas.</p>

<h3>Habitat Restoration</h3>
<ul>
<li>Replanting native vegetation along corridor routes</li>
<li>Removing invasive species</li>
<li>Creating water sources and shade areas</li>
<li>Installing wildlife-friendly fencing</li>
</ul>

<h3>Community Engagement</h3>
<p>Working with local communities to:</p>
<ul>
<li>Develop alternative livelihoods</li>
<li>Implement elephant-friendly farming practices</li>
<li>Create early warning systems</li>
<li>Establish community-based conservation groups</li>
</ul>

<h2>Current Impact</h2>
<ul>
<li>15 wildlife corridors established across 3 countries</li>
<li>200+ km of elephant pathways secured</li>
<li>60% reduction in human-elephant conflict incidents</li>
<li>500+ community members trained as wildlife monitors</li>
<li>12 elephant calves born in newly connected habitats</li>
</ul>

<h2>Technology and Innovation</h2>

<h3>Smart Monitoring Systems</h3>
<ul>
<li>Camera traps with AI-powered species identification</li>
<li>Acoustic monitoring for elephant communication</li>
<li>Drone surveillance for corridor maintenance</li>
<li>Mobile apps for community reporting</li>
</ul>

<h3>Conflict Prevention</h3>
<ul>
<li>Early warning SMS systems</li>
<li>Solar-powered deterrent devices</li>
<li>Bee-fence barriers (elephants avoid bees)</li>
<li>Chili-based elephant repellents</li>
</ul>

<h2>Partnerships</h2>
<p>This project succeeds through collaboration with:</p>
<ul>
<li>Government wildlife departments</li>
<li>Local communities and indigenous groups</li>
<li>International conservation organizations</li>
<li>Research institutions and universities</li>
<li>Private sector sponsors</li>
</ul>

<h2>Challenges and Solutions</h2>

<h3>Land Acquisition</h3>
<p><strong>Challenge:</strong> Securing corridor land from private owners<br>
<strong>Solution:</strong> Fair compensation schemes and conservation easements</p>

<h3>Funding Sustainability</h3>
<p><strong>Challenge:</strong> Long-term project funding<br>
<strong>Solution:</strong> Diversified funding from grants, carbon credits, and ecotourism</p>

<h3>Political Changes</h3>
<p><strong>Challenge:</strong> Policy changes affecting project continuity<br>
<strong>Solution:</strong> Multi-stakeholder agreements and legal protection</p>

<h2>Future Goals</h2>
<ul>
<li>Establish 25 additional corridors by 2025</li>
<li>Connect all major elephant populations in the region</li>
<li>Develop corridor management training programs</li>
<li>Create sustainable financing mechanisms</li>
<li>Expand to other species (tigers, orangutans)</li>
</ul>

<h2>How You Can Help</h2>
<ul>
<li>Adopt an elephant corridor</li>
<li>Support community-based conservation</li>
<li>Advocate for wildlife-friendly policies</li>
<li>Choose sustainable palm oil products</li>
<li>Visit responsible elephant tourism sites</li>
</ul>

<h2>Success Stories</h2>

<h3>The Leuser Corridor</h3>
<p>A 5-km corridor in Sumatra has enabled elephant families to safely access seasonal feeding grounds, reducing crop raiding by 80% and increasing local support for conservation.</p>

<h3>Community Champions</h3>
<p>Former poacher Somchai became a wildlife monitor after losing his crops to elephants. Now he leads early warning systems and has helped reduce conflicts in his village by 90%.</p>""",
            "excerpt": "Discover how Project Elephant Corridor is creating safe passage routes for Asian elephants, reducing human-wildlife conflict and connecting fragmented habitats across Southeast Asia.",
            "author_name": "Conservation Team",
            "featured_image": "/uploads/images/elephant-corridor-project.jpg",
            "slug": "elephant-corridor-habitat-connection",
            "tags": ["elephants", "corridors", "habitat", "conservation"],
            "type": ContentTypeEnum.CONSERVATION_EFFORT,
            "status": ContentStatusEnum.PUBLISHED
        },
        {
            "title": "Ocean Guardians: Protecting Marine Protected Areas",
            "content": """<h2>Mission Statement</h2>
<p>Ocean Guardians is a comprehensive marine conservation program dedicated to establishing, monitoring, and protecting Marine Protected Areas (MPAs) across critical ocean ecosystems. Our mission is to preserve marine biodiversity while supporting sustainable livelihoods for coastal communities.</p>

<h2>The Ocean Crisis</h2>
<p>Our oceans face unprecedented threats:</p>
<ul>
<li>Overfishing has depleted 90% of large fish populations</li>
<li>Climate change is causing ocean acidification and warming</li>
<li>Plastic pollution affects marine life at every level</li>
<li>Coastal development destroys critical habitats</li>
<li>Illegal fishing undermines conservation efforts</li>
</ul>

<h2>Our Approach</h2>

<h3>Science-Based Planning</h3>
<p>We use cutting-edge marine science to identify and design effective MPAs:</p>
<ul>
<li>Biodiversity hotspot mapping</li>
<li>Fish population assessments</li>
<li>Ocean current and connectivity analysis</li>
<li>Climate change vulnerability studies</li>
<li>Socio-economic impact evaluations</li>
</ul>

<h3>Community-Centered Conservation</h3>
<p>Local communities are at the heart of our conservation strategy:</p>
<ul>
<li>Co-management agreements with fishing communities</li>
<li>Alternative livelihood programs</li>
<li>Marine stewardship training</li>
<li>Traditional knowledge integration</li>
<li>Youth education and engagement</li>
</ul>

<h2>Current Projects</h2>

<h3>Coral Triangle Initiative</h3>
<p>Protecting the world's most biodiverse marine region across 6 countries:</p>
<ul>
<li>25 MPAs covering 50,000 km²</li>
<li>Protection of 500+ fish species</li>
<li>Coral reef restoration programs</li>
<li>Sustainable tourism development</li>
</ul>

<h3>Kelp Forest Recovery</h3>
<p>Restoring temperate marine ecosystems:</p>
<ul>
<li>Sea urchin population control</li>
<li>Kelp replanting initiatives</li>
<li>Predator species reintroduction</li>
<li>Water quality improvement</li>
</ul>

<h3>Seagrass Sanctuary Network</h3>
<p>Protecting critical nursery habitats:</p>
<ul>
<li>Mapping and monitoring seagrass beds</li>
<li>Boat strike prevention programs</li>
<li>Nutrient pollution reduction</li>
<li>Restoration of degraded areas</li>
</ul>

<h2>Technology and Innovation</h2>

<h3>Monitoring and Surveillance</h3>
<ul>
<li>Underwater drones for reef monitoring</li>
<li>Satellite tracking of fishing vessels</li>
<li>Environmental DNA sampling</li>
<li>Acoustic monitoring of marine life</li>
<li>AI-powered species identification</li>
</ul>

<h3>Enforcement Tools</h3>
<ul>
<li>Vessel monitoring systems</li>
<li>Radar and sonar detection</li>
<li>Night vision surveillance</li>
<li>Rapid response patrol boats</li>
<li>Community reporting apps</li>
</ul>

<h2>Impact and Results</h2>

<h3>Ecological Outcomes</h3>
<ul>
<li>40% increase in fish biomass within MPAs</li>
<li>Recovery of endangered species populations</li>
<li>Restoration of degraded habitats</li>
<li>Improved water quality indicators</li>
<li>Enhanced ecosystem resilience</li>
</ul>

<h3>Socio-Economic Benefits</h3>
<ul>
<li>Sustainable fishing practices adopted by 80% of local fishers</li>
<li>Ecotourism revenue increased by 150%</li>
<li>Creation of 500+ green jobs</li>
<li>Improved food security for coastal communities</li>
<li>Enhanced climate change adaptation</li>
</ul>

<h2>Challenges and Adaptive Management</h2>

<h3>Enforcement Challenges</h3>
<p><strong>Issue:</strong> Limited resources for patrolling vast ocean areas<br>
<strong>Solution:</strong> Community-based monitoring and technology integration</p>

<h3>Climate Change Impacts</h3>
<p><strong>Issue:</strong> Shifting species distributions and habitat changes<br>
<strong>Solution:</strong> Dynamic MPA boundaries and climate-adaptive management</p>

<h3>Economic Pressures</h3>
<p><strong>Issue:</strong> Short-term economic losses for fishing communities<br>
<strong>Solution:</strong> Compensation schemes and alternative livelihood programs</p>

<h2>Partnerships and Collaboration</h2>
<ul>
<li>Government marine agencies</li>
<li>International conservation organizations</li>
<li>Research institutions and universities</li>
<li>Fishing industry associations</li>
<li>Tourism operators</li>
<li>Local NGOs and community groups</li>
</ul>

<h2>Future Vision</h2>

<h3>2025 Goals</h3>
<ul>
<li>Establish 50 new MPAs</li>
<li>Protect 30% of critical marine habitats</li>
<li>Train 1,000 community marine guardians</li>
<li>Develop sustainable financing mechanisms</li>
<li>Create regional MPA networks</li>
</ul>

<h3>Innovation Pipeline</h3>
<ul>
<li>Blockchain-based fishing quotas</li>
<li>Autonomous underwater vehicles</li>
<li>Virtual reality education programs</li>
<li>Genetic rescue techniques</li>
<li>Blue carbon credit systems</li>
</ul>

<h2>Get Involved</h2>

<h3>For Individuals</h3>
<ul>
<li>Adopt a marine protected area</li>
<li>Participate in citizen science projects</li>
<li>Choose sustainable seafood</li>
<li>Reduce plastic consumption</li>
<li>Support marine conservation policies</li>
</ul>

<h3>For Organizations</h3>
<ul>
<li>Corporate sponsorship opportunities</li>
<li>Employee volunteer programs</li>
<li>Sustainable supply chain partnerships</li>
<li>Research collaboration</li>
<li>Technology development partnerships</li>
</ul>

<h2>Success Spotlight</h2>
<p>The Apo Island Marine Reserve in the Philippines, established through our program, has become a model for community-based marine conservation. Fish populations have increased by 300%, and the island now generates over $1 million annually from sustainable tourism while maintaining its cultural heritage and marine biodiversity.</p>""",
            "excerpt": "Learn about Ocean Guardians' comprehensive approach to marine conservation, establishing and protecting Marine Protected Areas while supporting coastal communities through science-based planning and community-centered strategies.",
            "author_name": "Marine Conservation Team",
            "featured_image": "/uploads/images/ocean-guardians-mpa.jpg",
            "slug": "ocean-guardians-marine-protected-areas",
            "tags": ["marine", "ocean", "protected-areas", "conservation"],
            "type": ContentTypeEnum.CONSERVATION_EFFORT,
            "status": ContentStatusEnum.PUBLISHED
        }
    ]
    
    async with get_db_session() as db:
        for i, effort_data in enumerate(conservation_efforts):
            category = random.choice(categories)
            effort_data["category_id"] = category.id
            
            conservation_effort = Content(**effort_data)
            db.add(conservation_effort)
        
        await db.commit()


async def create_daily_updates(categories):
    """Create sample daily updates"""
    daily_updates = []
    
    # Create updates for the past 10 days
    for i in range(10):
        date = datetime.now() - timedelta(days=i)
        
        updates_data = [
            {
                "title": f"Tiger Population Increases in Ranthambore National Park - {date.strftime('%B %d, %Y')}",
                "content": f"""<h2>Exciting News from Ranthambore</h2>
<p>Wildlife officials at Ranthambore National Park reported a significant increase in tiger sightings this week. Camera trap data reveals that the park's tiger population has grown to an estimated 75 individuals, marking a 15% increase from last year's count.</p>

<h3>Key Highlights</h3>
<ul>
<li>Three new tiger cubs spotted with their mother in Zone 3</li>
<li>Successful territorial establishment by young male tiger T-91</li>
<li>Improved prey base supporting larger tiger population</li>
<li>Enhanced anti-poaching measures showing positive results</li>
</ul>

<h3>Conservation Impact</h3>
<p>This population increase demonstrates the effectiveness of ongoing conservation efforts, including:</p>
<ul>
<li>Habitat restoration projects</li>
<li>Community engagement programs</li>
<li>Scientific monitoring and research</li>
<li>Tourism revenue supporting conservation</li>
</ul>

<p>The park authorities continue to monitor tiger movements and behavior to ensure sustainable population growth while maintaining ecological balance.</p>""",
                "excerpt": f"Ranthambore National Park reports a 15% increase in tiger population with 75 individuals now calling the park home, including three new cubs spotted this week.",
                "author_name": "Field Research Team",
                "featured_image": "/uploads/images/ranthambore-tigers.jpg",
                "slug": f"ranthambore-tiger-population-increase-{date.strftime('%Y-%m-%d')}",
                "tags": ["tigers", "ranthambore", "population-increase", "daily-update"],
                "type": ContentTypeEnum.DAILY_UPDATE,
                "status": ContentStatusEnum.PUBLISHED
            },
            {
                "title": f"Successful Sea Turtle Nesting Season on Gahirmatha Beach - {date.strftime('%B %d, %Y')}",
                "content": f"""<h2>Record-Breaking Nesting Season</h2>
<p>Gahirmatha Beach in Odisha, India, has witnessed its most successful Olive Ridley sea turtle nesting season in over a decade. More than 400,000 female turtles arrived for mass nesting (arribada) this year, compared to 300,000 last year.</p>

<h3>Conservation Achievements</h3>
<ul>
<li>Zero incidents of turtle mortality due to fishing nets</li>
<li>100% protection of nesting sites from human disturbance</li>
<li>Successful hatching rate of 85% recorded</li>
<li>Over 2 million hatchlings safely reached the ocean</li>
</ul>

<h3>Community Involvement</h3>
<p>Local fishing communities played a crucial role in this conservation success:</p>
<ul>
<li>Voluntary fishing moratorium during nesting season</li>
<li>Beach patrolling by community volunteers</li>
<li>Turtle-friendly fishing practices adopted</li>
<li>Alternative livelihood programs during moratorium</li>
</ul>

<h3>Ongoing Monitoring</h3>
<p>Satellite tagging of 50 adult females will help researchers track migration patterns and identify critical habitats for future protection efforts.</p>""",
                "excerpt": f"Gahirmatha Beach records its most successful sea turtle nesting season with over 400,000 Olive Ridley turtles and 2 million hatchlings safely reaching the ocean.",
                "author_name": "Marine Biology Team",
                "featured_image": "/uploads/images/gahirmatha-sea-turtles.jpg",
                "slug": f"gahirmatha-sea-turtle-nesting-success-{date.strftime('%Y-%m-%d')}",
                "tags": ["sea-turtles", "nesting", "gahirmatha", "conservation-success"],
                "type": ContentTypeEnum.DAILY_UPDATE,
                "status": ContentStatusEnum.PUBLISHED
            }
        ]
        
        daily_updates.extend(updates_data)
    
    async with get_db_session() as db:
        for update_data in daily_updates:
            category = random.choice(categories)
            update_data["category_id"] = category.id
            
            daily_update = Content(**update_data)
            db.add(daily_update)
        
        await db.commit()


async def create_myths_facts():
    """Create sample myths vs facts"""
    myths_facts = [
        {
            "title": "Shark Behavior and Human Interaction",
            "myth_content": "Sharks are mindless killing machines that actively hunt humans",
            "fact_content": "Sharks are intelligent predators that play a crucial role in marine ecosystems. Humans are not their preferred prey - most shark attacks are cases of mistaken identity. You're more likely to be struck by lightning than attacked by a shark.",
            "is_featured": True
        },
        {
            "title": "Snake Safety and Ecosystem Role",
            "myth_content": "All snakes are dangerous and should be killed on sight",
            "fact_content": "Only about 15% of snake species worldwide are venomous, and even fewer pose a serious threat to humans. Snakes are vital for ecosystem balance, controlling rodent populations that would otherwise damage crops and spread disease.",
            "is_featured": True
        },
        {
            "title": "Bat Navigation and Benefits",
            "myth_content": "Bats are blind and will get tangled in your hair",
            "fact_content": "Bats have excellent vision and use sophisticated echolocation to navigate. They are incredibly agile flyers and will never intentionally fly into your hair. Most bats are beneficial, eating thousands of insects per night or pollinating important plants.",
            "is_featured": False
        },
        {
            "title": "Wolf Ecology and Human Safety",
            "myth_content": "Wolves are a threat to humans and livestock, and their reintroduction harms ecosystems",
            "fact_content": "Wolves rarely attack humans and their reintroduction actually helps restore ecosystem balance. They control deer populations, which allows vegetation to recover, benefiting many other species. Proper management can minimize livestock conflicts.",
            "is_featured": True
        },
        {
            "title": "Climate Change Origins",
            "myth_content": "Climate change is natural and not caused by human activities",
            "fact_content": "Current climate change is primarily caused by human activities, particularly burning fossil fuels. The rate of change is unprecedented in human history and is already affecting wildlife through habitat loss, changing migration patterns, and ecosystem disruption.",
            "is_featured": True
        },
        {
            "title": "Bird Parental Care",
            "myth_content": "Touching a baby bird will cause its parents to abandon it",
            "fact_content": "Most birds have a poor sense of smell and will not abandon their young if touched by humans. However, it's still best to avoid handling baby birds unless they're clearly injured, as human intervention is usually unnecessary and can be stressful.",
            "is_featured": False
        },
        {
            "title": "Elephant Fears",
            "myth_content": "Elephants are afraid of mice",
            "fact_content": "Elephants are not afraid of mice. This myth likely originated from cartoons and has no basis in reality. Elephants are intelligent animals that are cautious around unfamiliar small objects, but they show no special fear of mice specifically.",
            "is_featured": False
        },
        {
            "title": "Goldfish Memory",
            "myth_content": "Goldfish have a 3-second memory",
            "fact_content": "Goldfish can remember things for months, not seconds. They can be trained to respond to different colors, sounds, and cues. Studies have shown goldfish can remember feeding schedules and recognize their owners.",
            "is_featured": False
        }
    ]
    
    async with get_db_session() as db:
        for myth_fact_data in myths_facts:
            myth_fact = MythFact(**myth_fact_data)
            db.add(myth_fact)
        
        await db.commit()


async def create_sample_media():
    """Create sample media entries for testing"""
    media_entries = [
        {
            "media_type": "IMAGE",
            "file_url": "/uploads/images/bengal-tiger-sundarbans.jpg",
            "thumbnail_url": "/uploads/thumbnails/thumb_bengal-tiger-sundarbans.jpg",
            "title": "Bengal Tiger in Sundarbans",
            "description": "A majestic Bengal tiger prowling through the mangrove forests of Sundarbans National Park",
            "photographer": "Rajesh Kumar",
            "national_park": "Sundarbans National Park",
            "file_size": 2048000,
            "width": 1920,
            "height": 1280,
            "is_featured": 1
        },
        {
            "media_type": "IMAGE",
            "file_url": "/uploads/images/coral-reef-maldives.jpg",
            "thumbnail_url": "/uploads/thumbnails/thumb_coral-reef-maldives.jpg",
            "title": "Vibrant Coral Reef",
            "description": "Colorful coral reef ecosystem teeming with marine life in the crystal clear waters of Maldives",
            "photographer": "Sarah Johnson",
            "national_park": "Maldives Marine Reserve",
            "file_size": 3072000,
            "width": 2560,
            "height": 1440,
            "is_featured": 2
        },
        {
            "media_type": "IMAGE",
            "file_url": "/uploads/images/african-elephant-herd.jpg",
            "thumbnail_url": "/uploads/thumbnails/thumb_african-elephant-herd.jpg",
            "title": "African Elephant Family",
            "description": "A family of African elephants crossing the savanna during the great migration",
            "photographer": "Michael Thompson",
            "national_park": "Serengeti National Park",
            "file_size": 2560000,
            "width": 2048,
            "height": 1365,
            "is_featured": 3
        },
        {
            "media_type": "PODCAST",
            "file_url": "/uploads/audio/wildlife-sounds-rainforest.mp3",
            "thumbnail_url": "/uploads/thumbnails/thumb_rainforest-podcast.jpg",
            "title": "Sounds of the Amazon Rainforest",
            "description": "Immerse yourself in the natural symphony of the Amazon rainforest with bird calls, insect sounds, and flowing water",
            "photographer": "Dr. Maria Santos",
            "national_park": "Amazon Rainforest Reserve",
            "file_size": 45000000,
            "duration": 1800,
            "is_featured": 1
        },
        {
            "media_type": "PODCAST",
            "file_url": "/uploads/audio/conservation-stories-tigers.mp3",
            "thumbnail_url": "/uploads/thumbnails/thumb_tiger-conservation-podcast.jpg",
            "title": "Tiger Conservation Success Stories",
            "description": "Inspiring stories of tiger conservation efforts across India and their remarkable recovery",
            "photographer": "Priya Sharma",
            "national_park": "Various Tiger Reserves",
            "file_size": 52000000,
            "duration": 2100,
            "is_featured": 2
        },
        {
            "media_type": "VIDEO",
            "file_url": "/uploads/videos/whale-migration-documentary.mp4",
            "thumbnail_url": "/uploads/thumbnails/thumb_whale-migration.jpg",
            "title": "The Great Whale Migration",
            "description": "Follow humpback whales on their incredible 25,000-mile journey from feeding to breeding grounds",
            "photographer": "Ocean Documentary Team",
            "national_park": "Pacific Marine Sanctuary",
            "file_size": 150000000,
            "duration": 900,
            "width": 1920,
            "height": 1080
        }
    ]
    
    async with get_db_session() as db:
        for media_data in media_entries:
            media = Media(**media_data)
            db.add(media)
        
        await db.commit()


async def create_test_user():
    """Create a test user for content"""
    async with get_db_session() as db:
        # Check if test user already exists
        from sqlalchemy import select
        result = await db.execute(
            select(User).where(User.email == "admin@junglore.com")
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print("Found existing admin user")
            return existing_user.id
        
        # Create new test user
        from app.core.security import get_password_hash
        test_user = User(
            email="admin@junglore.com",
            username="admin",
            full_name="Admin User",
            hashed_password=get_password_hash("admin123"),
            is_active=True,
            is_superuser=True
        )
        
        db.add(test_user)
        await db.commit()
        await db.refresh(test_user)
        
        print("Created test admin user")
        return test_user.id


async def main():
    """Main function to populate all test data"""
    try:
        print("Starting test data population...")
        
        print("Creating test user...")
        test_user_id = await create_test_user()
        print(f"Test user ready")
        
        print("Creating categories...")
        categories = await create_categories()
        print(f"Created {len(categories)} categories")
        
        # print("Creating blog posts...")
        # await create_blog_posts(categories, test_user_id)
        # print("Blog posts created")
        
        # print("Creating case studies...")
        # await create_case_studies(categories)
        # print("Case studies created")
        
        # print("Creating conservation efforts...")
        # await create_conservation_efforts(categories)
        # print("Conservation efforts created")
        
        # print("Creating daily updates...")
        # await create_daily_updates(categories)
        # print("Daily updates created")
        
        print("Creating myths vs facts...")
        await create_myths_facts()
        print("Myths vs facts created")
        
        print("Creating sample media...")
        await create_sample_media()
        print("Sample media created")
        
        print("Test data population completed successfully!")
        
    except Exception as e:
        print(f"Error populating test data: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())