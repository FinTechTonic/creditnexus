/**
 * Social newsfeed: deals/markets posts, like, comment, share, Fund button, and link to Polymarket.
 * Week 13: Fund uses funding-options by asset type and POST /api/newsfeed/fund (402 handled by PaymentContext).
 */

import { useState, useEffect, useCallback } from 'react';
import { Heart, MessageCircle, Share2, ExternalLink, DollarSign } from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import { usePayment } from '@/context/PaymentContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface FundingOption {
  id: string;
  payment_type: string;
  label: string;
  description: string;
}

interface NewsfeedPost {
  id: number;
  post_type: string;
  title: string;
  content: string | null;
  polymarket_market_url?: string | null;
  likes_count: number;
  comments_count: number;
  user_liked: boolean;
  author: { id: number; display_name?: string; email?: string } | null;
  deal: Record<string, unknown> | null;
  market: { id: number; market_id: string; question: string } | null;
  created_at: string | null;
}

function assetTypeFromPost(post: NewsfeedPost): string {
  if (post.post_type === 'market_created') return 'market';
  if (post.post_type === 'deal_published') return 'loan';
  if (post.deal?.deal_type) return (post.deal.deal_type as string).toLowerCase();
  return 'default';
}

export function Newsfeed() {
  const { fetchWithPaymentHandling } = usePayment();
  const [posts, setPosts] = useState<NewsfeedPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [postType, setPostType] = useState('');
  const [dealType, setDealType] = useState('');
  const [commentPostId, setCommentPostId] = useState<number | null>(null);
  const [commentContent, setCommentContent] = useState('');
  const [commentLoading, setCommentLoading] = useState(false);
  const [fundPostId, setFundPostId] = useState<number | null>(null);
  const [fundAmount, setFundAmount] = useState('');
  const [fundOption, setFundOption] = useState<string>('');
  const [fundingOptions, setFundingOptions] = useState<FundingOption[]>([]);
  const [fundLoading, setFundLoading] = useState(false);
  const [fundStatus, setFundStatus] = useState<string | null>(null);

  const loadNewsfeed = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (postType) params.set('post_type', postType);
      if (dealType) params.set('deal_type', dealType);
      params.set('limit', '20');
      params.set('offset', '0');
      const response = await fetchWithAuth(`/api/newsfeed?${params.toString()}`);
      if (response.ok) {
        const data = await response.json();
        setPosts(data.posts ?? []);
      } else {
        setPosts([]);
      }
    } catch {
      setPosts([]);
    } finally {
      setLoading(false);
    }
  }, [postType, dealType]);

  useEffect(() => {
    loadNewsfeed();
  }, [loadNewsfeed]);

  const handleLike = async (postId: number) => {
    try {
      const response = await fetchWithAuth(`/api/newsfeed/posts/${postId}/like`, { method: 'POST' });
      if (response.ok) {
        loadNewsfeed();
      }
    } catch (e) {
      console.error('Failed to like post', e);
    }
  };

  const handleOpenPolymarket = (url: string) => {
    window.open(url, '_blank');
  };

  const handleCommentSubmit = async (postId: number) => {
    if (!commentContent.trim()) return;
    setCommentLoading(true);
    try {
      const response = await fetchWithAuth(`/api/newsfeed/posts/${postId}/comment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: commentContent.trim(), parent_comment_id: null }),
      });
      if (response.ok) {
        setCommentContent('');
        setCommentPostId(null);
        loadNewsfeed();
      }
    } catch (e) {
      console.error('Failed to comment', e);
    } finally {
      setCommentLoading(false);
    }
  };

  const handleShare = async (postId: number) => {
    try {
      await fetchWithAuth(`/api/newsfeed/posts/${postId}/share`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ share_type: 'internal' }),
      });
      loadNewsfeed();
    } catch (e) {
      console.error('Failed to share', e);
    }
  };

  const handleFundClick = useCallback(
    async (post: NewsfeedPost) => {
      if (fundPostId === post.id) {
        setFundPostId(null);
        setFundAmount('');
        setFundOption('');
        setFundingOptions([]);
        setFundStatus(null);
        return;
      }
      setFundPostId(post.id);
      setFundAmount('');
      setFundOption('');
      setFundStatus(null);
      const assetType = assetTypeFromPost(post);
      try {
        const r = await fetchWithAuth(
          `/api/newsfeed/funding-options/${encodeURIComponent(assetType)}`
        );
        if (r.ok) {
          const data = await r.json();
          const opts = data.options ?? [];
          setFundingOptions(opts);
          if (opts.length) setFundOption(opts[0].payment_type);
        } else {
          setFundingOptions([]);
        }
      } catch {
        setFundingOptions([]);
      }
    },
    [fundPostId]
  );

  const handleFundSubmit = async (postId: number) => {
    const amount = parseFloat(fundAmount);
    if (!amount || amount <= 0 || !fundOption) return;
    setFundLoading(true);
    setFundStatus(null);
    try {
      const r = await fetchWithPaymentHandling('/api/newsfeed/fund', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          post_id: postId,
          amount: amount.toFixed(2),
          payment_type: fundOption,
        }),
      });
      if (r.status === 402) {
        setFundStatus('Payment required – complete in the payment modal.');
        return;
      }
      if (r.ok) {
        const data = await r.json();
        setFundStatus(data.status === 'settled' ? 'Funding completed.' : 'Funding initiated.');
        setFundAmount('');
        setFundPostId(null);
      } else {
        const err = await r.json().catch(() => ({}));
        setFundStatus(err.detail || 'Funding request failed.');
      }
    } catch (e) {
      setFundStatus('Funding request failed.');
      console.error(e);
    } finally {
      setFundLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-semibold text-slate-100">Newsfeed</h2>
        <div className="flex gap-2">
          <select
            value={postType}
            onChange={(e) => setPostType(e.target.value)}
            className="px-4 py-2 bg-slate-900 border border-slate-600 rounded text-slate-100"
          >
            <option value="">All Types</option>
            <option value="market_created">Markets</option>
            <option value="deal_published">Deals</option>
          </select>
          <select
            value={dealType}
            onChange={(e) => setDealType(e.target.value)}
            className="px-4 py-2 bg-slate-900 border border-slate-600 rounded text-slate-100"
          >
            <option value="">All Deal Types</option>
            <option value="loan_application">Loan</option>
            <option value="debt_sale">Debt Sale</option>
          </select>
        </div>
      </div>

      {loading ? (
        <p className="text-slate-400">Loading newsfeed…</p>
      ) : (
        <div className="space-y-4">
          {posts.map((post) => (
            <Card key={post.id} className="p-6 bg-slate-900/50 border-slate-700">
              <CardContent className="p-0">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="text-lg font-semibold text-slate-100 mb-2">{post.title}</h3>
                    {post.content && (
                      <p className="text-slate-400 text-sm mb-2">{post.content}</p>
                    )}
                    <div className="flex items-center gap-4 text-xs text-slate-500">
                      <span>
                        By {post.author?.display_name ?? post.author?.email ?? `User #${post.author?.id ?? post.id}`}
                      </span>
                      <span>•</span>
                      <span>
                        {post.created_at
                          ? new Date(post.created_at).toLocaleDateString()
                          : ''}
                      </span>
                    </div>
                  </div>
                  <div className="flex gap-2 shrink-0">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleFundClick(post)}
                      className={fundPostId === post.id ? 'ring-2 ring-emerald-500' : ''}
                    >
                      <DollarSign className="h-4 w-4 mr-2" />
                      Fund
                    </Button>
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
                </div>

                {fundPostId === post.id && (
                  <div className="mt-4 pt-4 border-t border-slate-700">
                    <Label className="text-slate-300">Fund this product</Label>
                    <div className="flex flex-wrap items-end gap-3 mt-2">
                      <div>
                        <Label className="text-xs text-slate-500">Amount (USD)</Label>
                        <Input
                          type="number"
                          min="0.01"
                          step="0.01"
                          value={fundAmount}
                          onChange={(e) => setFundAmount(e.target.value)}
                          placeholder="0.00"
                          className="mt-1 w-28 bg-slate-800 border-slate-600 text-slate-100"
                        />
                      </div>
                      {fundingOptions.length > 0 && (
                        <div>
                          <Label className="text-xs text-slate-500">Method</Label>
                          <select
                            value={fundOption}
                            onChange={(e) => setFundOption(e.target.value)}
                            className="mt-1 px-3 py-2 bg-slate-800 border border-slate-600 rounded text-slate-100"
                          >
                            {fundingOptions.map((opt) => (
                              <option key={opt.id} value={opt.payment_type}>
                                {opt.label}
                              </option>
                            ))}
                          </select>
                        </div>
                      )}
                      <Button
                        size="sm"
                        onClick={() => handleFundSubmit(post.id)}
                        disabled={!fundAmount || parseFloat(fundAmount) <= 0 || !fundOption || fundLoading}
                      >
                        {fundLoading ? 'Processing…' : 'Submit'}
                      </Button>
                    </div>
                    {fundStatus && (
                      <p className="mt-2 text-sm text-slate-400">{fundStatus}</p>
                    )}
                  </div>
                )}

                <div className="flex items-center gap-4 pt-4 border-t border-slate-700">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleLike(post.id)}
                    className={post.user_liked ? 'text-red-400' : 'text-slate-400'}
                  >
                    <Heart
                      className={`h-4 w-4 mr-2 ${post.user_liked ? 'fill-current' : ''}`}
                    />
                    {post.likes_count}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() =>
                      setCommentPostId(commentPostId === post.id ? null : post.id)
                    }
                    className="text-slate-400"
                  >
                    <MessageCircle className="h-4 w-4 mr-2" />
                    {post.comments_count}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleShare(post.id)}
                    className="text-slate-400"
                  >
                    <Share2 className="h-4 w-4 mr-2" />
                    Share
                  </Button>
                </div>

                {commentPostId === post.id && (
                  <div className="mt-4 pt-4 border-t border-slate-700">
                    <Label className="text-slate-300">Add a comment</Label>
                    <div className="flex gap-2 mt-2">
                      <Input
                        value={commentContent}
                        onChange={(e) => setCommentContent(e.target.value)}
                        placeholder="Write a comment…"
                        className="bg-slate-800 border-slate-600 text-slate-100"
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleCommentSubmit(post.id);
                        }}
                      />
                      <Button
                        size="sm"
                        onClick={() => handleCommentSubmit(post.id)}
                        disabled={!commentContent.trim() || commentLoading}
                      >
                        {commentLoading ? 'Sending…' : 'Send'}
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
          {posts.length === 0 && (
            <p className="text-slate-400">No posts yet. Markets and deals will appear here when created.</p>
          )}
        </div>
      )}
    </div>
  );
}
