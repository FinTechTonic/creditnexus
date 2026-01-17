# Social Newsfeed Plan
## Polymarket Deal Discovery & Interaction

**Status**: Comprehensive Enhancement Plan  
**Priority**: P0 (Critical)  
**Estimated Timeline**: 6-8 weeks  
**Last Updated**: 2024-12-XX

---

## Executive Summary

This plan implements a **social newsfeed** where:
1. **Deal Discovery**: Deals published on Polymarket are visible in a social newsfeed
2. **Market Linking**: Direct links to Polymarket dashboard for trading/interaction
3. **Social Features**: Like, comment, share, and follow functionality
4. **Real-Time Updates**: Live updates when new markets are created
5. **Filtering & Search**: Filter by deal type, organization, market status

---

## Current State Analysis

### Existing Infrastructure

**Polymarket Integration**:
- **Location**: `dev/POLYMARKET_INTEGRATION_PLAN.md`
- **Current**: Market creation, API integration
- **Gap**: No social newsfeed for market discovery

**Deal Management**:
- **Location**: `app/db/models.py` (Deal model)
- **Current**: Deal tracking and lifecycle management
- **Gap**: No social features or newsfeed

**Workflow Sharing**:
- **Location**: `app/services/workflow_delegation_service.py`
- **Current**: Workflow link sharing
- **Gap**: No social newsfeed integration

---

## Project 1: Newsfeed Database Models

### Activity 1.1: Newsfeed Models

**File**: `app/db/models.py` (UPDATE)

#### Task 1.1.1: Add Newsfeed Models
**Lines**: ~3000-3200

**Subtasks**:
1. **Line 3000-3200**: Newsfeed models
   ```python
   class NewsfeedPost(Base):
       """Newsfeed post for deals and markets."""
       __tablename__ = "newsfeed_posts"
       
       id = Column(Integer, primary_key=True)
       
       # Post content
       post_type = Column(String(50), nullable=False, index=True)  # market_created, deal_published, market_resolved, etc.
       title = Column(String(500), nullable=False)
       content = Column(Text, nullable=True)
       
       # Associated entities
       deal_id = Column(Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=True, index=True)
       market_id = Column(Integer, ForeignKey("market_events.id", ondelete="CASCADE"), nullable=True, index=True)
       organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
       
       # Author
       author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True)
       
       # Polymarket integration
       polymarket_market_id = Column(String(255), nullable=True, index=True)  # Polymarket market ID
       polymarket_market_url = Column(String(500), nullable=True)  # Direct link to Polymarket
       
       # Engagement metrics
       likes_count = Column(Integer, default=0, nullable=False)
       comments_count = Column(Integer, default=0, nullable=False)
       shares_count = Column(Integer, default=0, nullable=False)
       views_count = Column(Integer, default=0, nullable=False)
       
       # Visibility
       visibility = Column(String(20), default="public", nullable=False)  # public, organization, private
       is_pinned = Column(Boolean, default=False, nullable=False)
       
       # Metadata
       metadata = Column(JSONB, nullable=True)  # Additional post data
       
       created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
       updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
       
       # Relationships
       deal = relationship("Deal", backref="newsfeed_posts")
       market = relationship("MarketEvent", backref="newsfeed_posts")
       organization = relationship("Organization", backref="newsfeed_posts")
       author = relationship("User", foreign_keys=[author_id])
       likes = relationship("NewsfeedLike", back_populates="post", cascade="all, delete-orphan")
       comments = relationship("NewsfeedComment", back_populates="post", cascade="all, delete-orphan")
       shares = relationship("NewsfeedShare", back_populates="post", cascade="all, delete-orphan")
   
   class NewsfeedLike(Base):
       """Like on newsfeed post."""
       __tablename__ = "newsfeed_likes"
       
       id = Column(Integer, primary_key=True)
       post_id = Column(Integer, ForeignKey("newsfeed_posts.id", ondelete="CASCADE"), nullable=False, index=True)
       user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
       created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
       
       # Unique constraint
       __table_args__ = (
           UniqueConstraint('post_id', 'user_id', name='uq_newsfeed_like_post_user'),
       )
       
       # Relationships
       post = relationship("NewsfeedPost", back_populates="likes")
       user = relationship("User")
   
   class NewsfeedComment(Base):
       """Comment on newsfeed post."""
       __tablename__ = "newsfeed_comments"
       
       id = Column(Integer, primary_key=True)
       post_id = Column(Integer, ForeignKey("newsfeed_posts.id", ondelete="CASCADE"), nullable=False, index=True)
       user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True)
       parent_comment_id = Column(Integer, ForeignKey("newsfeed_comments.id", ondelete="CASCADE"), nullable=True)  # For replies
       content = Column(Text, nullable=False)
       created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
       updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
       
       # Relationships
       post = relationship("NewsfeedPost", back_populates="comments")
       user = relationship("User")
       parent_comment = relationship("NewsfeedComment", remote_side=[id], backref="replies")
   
   class NewsfeedShare(Base):
       """Share of newsfeed post."""
       __tablename__ = "newsfeed_shares"
       
       id = Column(Integer, primary_key=True)
       post_id = Column(Integer, ForeignKey("newsfeed_posts.id", ondelete="CASCADE"), nullable=False, index=True)
       user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True)
       share_type = Column(String(20), default="internal", nullable=False)  # internal, external, fdc3
       shared_to = Column(String(500), nullable=True)  # Email, FDC3 app, etc.
       created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
       
       # Relationships
       post = relationship("NewsfeedPost", back_populates="shares")
       user = relationship("User")
   ```

---

## Project 2: Newsfeed Service

### Activity 2.1: Newsfeed Service

**File**: `app/services/newsfeed_service.py` (NEW)

#### Task 2.1.1: Create Newsfeed Service
**Lines**: 1-500

**Subtasks**:
1. **Line 1-200**: Service class
   ```python
   class NewsfeedService:
       """Service for managing newsfeed posts and social interactions."""
       
       def __init__(self, db: Session):
           self.db = db
           self.polymarket_service = PolymarketService(db)
       
       async def create_market_post(
           self,
           market_id: int,
           author_id: int
       ) -> NewsfeedPost:
           """Create newsfeed post when market is created on Polymarket.
           
           Args:
               market_id: MarketEvent ID
               author_id: User ID of market creator
               
           Returns:
               Created NewsfeedPost
           """
           market = self.db.query(MarketEvent).filter(
               MarketEvent.id == market_id
           ).first()
           
           if not market:
               raise ValueError(f"Market {market_id} not found")
           
           # Get Polymarket market URL
           polymarket_url = f"https://polymarket.com/event/{market.polymarket_market_id}"
           
           # Create post
           post = NewsfeedPost(
               post_type="market_created",
               title=f"New Market: {market.question}",
               content=f"Market created for deal {market.deal_id}",
               deal_id=market.deal_id,
               market_id=market.id,
               author_id=author_id,
               polymarket_market_id=market.polymarket_market_id,
               polymarket_market_url=polymarket_url,
               visibility="public"
           )
           
           self.db.add(post)
           self.db.commit()
           self.db.refresh(post)
           
           return post
       
       async def get_newsfeed(
           self,
           user_id: int,
           organization_id: Optional[int] = None,
           limit: int = 20,
           offset: int = 0,
           filters: Optional[Dict[str, Any]] = None
       ) -> List[Dict[str, Any]]:
           """Get newsfeed posts for user.
           
           Args:
               user_id: User ID
               organization_id: Optional organization filter
               limit: Number of posts to return
               offset: Pagination offset
               filters: Optional filters (post_type, deal_type, etc.)
               
           Returns:
               List of newsfeed posts with engagement data
           """
           user = self.db.query(User).filter(User.id == user_id).first()
           
           # Build query
           query = self.db.query(NewsfeedPost)
           
           # Filter by visibility
           if organization_id:
               query = query.filter(
                   or_(
                       NewsfeedPost.visibility == "public",
                       and_(
                           NewsfeedPost.visibility == "organization",
                           NewsfeedPost.organization_id == organization_id
                       )
                   )
               )
           else:
               query = query.filter(NewsfeedPost.visibility == "public")
           
           # Apply filters
           if filters:
               if filters.get("post_type"):
                   query = query.filter(NewsfeedPost.post_type == filters["post_type"])
               if filters.get("deal_type"):
                   query = query.join(Deal).filter(Deal.deal_type == filters["deal_type"])
           
           # Order by created_at (newest first)
           query = query.order_by(NewsfeedPost.is_pinned.desc(), NewsfeedPost.created_at.desc())
           
           # Paginate
           posts = query.offset(offset).limit(limit).all()
           
           # Enrich with user engagement
           result = []
           for post in posts:
               user_liked = self.db.query(NewsfeedLike).filter(
                   NewsfeedLike.post_id == post.id,
                   NewsfeedLike.user_id == user_id
               ).first() is not None
               
               result.append({
                   **post.to_dict(),
                   "user_liked": user_liked,
                   "author": post.author.to_dict() if post.author else None,
                   "deal": post.deal.to_dict() if post.deal else None,
                   "market": post.market.to_dict() if post.market else None
               })
           
           return result
   ```

---

## Project 3: Newsfeed UI Component

### Activity 3.1: Newsfeed Component

**File**: `client/src/components/dashboard-tabs/Newsfeed.tsx` (NEW)

#### Task 3.1.1: Create Newsfeed Component
**Lines**: 1-600

**Subtasks**:
1. **Line 1-200**: Component setup
   ```typescript
   import { useState, useEffect } from 'react';
   import { Heart, MessageCircle, Share2, ExternalLink, TrendingUp } from 'lucide-react';
   import { fetchWithAuth } from '@/context/AuthContext';
   import { Button } from '@/components/ui/button';
   import { Card } from '@/components/ui/card';
   
   interface NewsfeedPost {
     id: number;
     post_type: string;
     title: string;
     content: string;
     polymarket_market_url?: string;
     likes_count: number;
     comments_count: number;
     user_liked: boolean;
     author: any;
     deal: any;
     market: any;
     created_at: string;
   }
   
   export function Newsfeed() {
     const [posts, setPosts] = useState<NewsfeedPost[]>([]);
     const [loading, setLoading] = useState(false);
     const [filters, setFilters] = useState({
       post_type: '',
       deal_type: ''
     });
     
     useEffect(() => {
       loadNewsfeed();
     }, [filters]);
     
     const loadNewsfeed = async () => {
       setLoading(true);
       try {
         const response = await fetchWithAuth(
           `/api/newsfeed?${new URLSearchParams(filters as any)}`
         );
         if (response.ok) {
           const data = await response.json();
           setPosts(data.posts || []);
         }
       } catch (error) {
         console.error('Failed to load newsfeed:', error);
       } finally {
         setLoading(false);
       }
     };
   ```

2. **Line 201-400**: Post rendering
   ```typescript
     const handleLike = async (postId: number) => {
       try {
         const response = await fetchWithAuth(`/api/newsfeed/posts/${postId}/like`, {
           method: 'POST'
         });
         if (response.ok) {
           loadNewsfeed(); // Reload to update counts
         }
       } catch (error) {
         console.error('Failed to like post:', error);
       }
     };
     
     const handleOpenPolymarket = (url: string) => {
       window.open(url, '_blank');
     };
     
     return (
       <div className="space-y-6">
         <div className="flex items-center justify-between mb-6">
           <h2 className="text-2xl font-semibold text-slate-100">Newsfeed</h2>
           <div className="flex gap-2">
             <select
               value={filters.post_type}
               onChange={(e) => setFilters({ ...filters, post_type: e.target.value })}
               className="px-4 py-2 bg-slate-900 border border-slate-600 rounded"
             >
               <option value="">All Types</option>
               <option value="market_created">Markets</option>
               <option value="deal_published">Deals</option>
             </select>
           </div>
         </div>
         
         <div className="space-y-4">
           {posts.map((post) => (
             <Card key={post.id} className="p-6">
               <div className="flex items-start justify-between mb-4">
                 <div>
                   <h3 className="text-lg font-semibold text-slate-100 mb-2">
                     {post.title}
                   </h3>
                   <p className="text-slate-400 text-sm mb-2">{post.content}</p>
                   <div className="flex items-center gap-4 text-xs text-slate-500">
                     <span>By {post.author?.display_name}</span>
                     <span>•</span>
                     <span>{new Date(post.created_at).toLocaleDateString()}</span>
                   </div>
                 </div>
                 {post.polymarket_market_url && (
                   <Button
                     variant="outline"
                     size="sm"
                     onClick={() => handleOpenPolymarket(post.polymarket_market_url!)}
                   >
                     <ExternalLink className="h-4 w-4 mr-2" />
                     Trade on Polymarket
                   </Button>
                 )}
               </div>
               
               <div className="flex items-center gap-4 pt-4 border-t border-slate-700">
                 <Button
                   variant="ghost"
                   size="sm"
                   onClick={() => handleLike(post.id)}
                   className={post.user_liked ? 'text-red-400' : ''}
                 >
                   <Heart className={`h-4 w-4 mr-2 ${post.user_liked ? 'fill-current' : ''}`} />
                   {post.likes_count}
                 </Button>
                 <Button variant="ghost" size="sm">
                   <MessageCircle className="h-4 w-4 mr-2" />
                   {post.comments_count}
                 </Button>
                 <Button variant="ghost" size="sm">
                   <Share2 className="h-4 w-4 mr-2" />
                   Share
                 </Button>
               </div>
             </Card>
           ))}
         </div>
       </div>
     );
   }
   ```

---

## Project 4: Auto-Post on Market Creation

### Activity 4.1: Integrate with Polymarket Service

**File**: `app/services/polymarket_service.py` (UPDATE)

#### Task 4.1.1: Auto-Create Newsfeed Post
**Lines**: ~200-250 (in create_market method)

**Subtasks**:
1. **Line 200-250**: Add newsfeed post creation
   ```python
   # After market creation in create_market method:
   
   # Create newsfeed post
   from app.services.newsfeed_service import NewsfeedService
   newsfeed_service = NewsfeedService(self.db)
   await newsfeed_service.create_market_post(
       market_id=market.id,
       author_id=creator_user_id
   )
   ```

---

## Implementation Checklist

### Phase 1: Database Models (Week 1)
- [ ] Create NewsfeedPost model
- [ ] Create NewsfeedLike model
- [ ] Create NewsfeedComment model
- [ ] Create NewsfeedShare model
- [ ] Create Alembic migration

### Phase 2: Newsfeed Service (Week 2-3)
- [ ] Create NewsfeedService
- [ ] Implement post creation
- [ ] Implement newsfeed retrieval
- [ ] Implement like/comment/share functionality

### Phase 3: Newsfeed UI (Week 4-5)
- [ ] Create Newsfeed component
- [ ] Add to UnifiedDashboard
- [ ] Implement post rendering
- [ ] Implement engagement actions

### Phase 4: Polymarket Integration (Week 6)
- [ ] Auto-create posts on market creation
- [ ] Add Polymarket links
- [ ] Test integration

### Phase 5: Testing & Refinement (Week 7-8)
- [ ] Test newsfeed functionality
- [ ] Test Polymarket linking
- [ ] Performance optimization
- [ ] User testing

---

**Last Updated**: 2024-12-XX  
**Version**: 1.0  
**Status**: Ready for Implementation
