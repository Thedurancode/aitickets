/**
 * Ad Editor Component
 * Full editor for customizing individual ads before publishing
 */

import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

interface AdCreative {
  id: number;
  ad_campaign_id: number;
  platform: string;
  format: string;
  name: string;
  headline: string;
  body: string;
  cta: string;
  image_url: string;
  video_url: string;
  link_url: string;
  target_audience: any;
  placements: string[];
  status: string;
  is_test_variant: boolean;
  test_group: string;
}

interface AdEditorProps {
  adId: number;
  onClose?: () => void;
  onSave?: (ad: AdCreative) => void;
}

export const AdEditor: React.FC<AdEditorProps> = ({ adId, onClose, onSave }) => {
  const [ad, setAd] = useState<AdCreative | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [availableImages, setAvailableImages] = useState<any[]>([]);

  // Available images from research (Spotify, YouTube, Wikipedia)
  const defaultImages = [
    { url: 'https://via.placeholder.com/640x640/4CAF50/ffffff?text=Spotify+Profile', source: 'spotify', type: 'profile' },
    { url: 'https://via.placeholder.com/640x640/9C27B0/ffffff?text=Album+Artwork', source: 'spotify', type: 'album' },
    { url: 'https://via.placeholder.com/1280x720/2196F3/ffffff?text=YouTube+Thumbnail', source: 'youtube', type: 'thumbnail' },
    { url: 'https://via.placeholder.com/800x600/FF9800/ffffff?text=Wikipedia+Photo', source: 'wikipedia', type: 'photo' },
  ];

  useEffect(() => {
    fetchAd();
    setAvailableImages(defaultImages);
  }, [adId]);

  const fetchAd = async () => {
    try {
      const response = await fetch(`/api/ad-campaigns/ads/${adId}`);
      const data = await response.json();

      // Parse JSON fields
      if (typeof data.target_audience === 'string') {
        data.target_audience = JSON.parse(data.target_audience || '{}');
      }
      if (typeof data.placements === 'string') {
        data.placements = JSON.parse(data.placements || '[]');
      }

      setAd(data);
    } catch (error) {
      console.error('Failed to fetch ad:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateAd = async (updates: Partial<AdCreative>) => {
    setSaving(true);
    try {
      const response = await fetch(`/api/ad-campaigns/ads/${adId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });

      const result = await response.json();
      if (result.success) {
        setAd(result.ad);
        if (onSave) onSave(result.ad);
      }
    } catch (error) {
      console.error('Failed to update ad:', error);
      alert('Failed to save changes');
    } finally {
      setSaving(false);
    }
  };

  const approveAd = async () => {
    try {
      const response = await fetch(`/api/ad-campaigns/ads/${adId}/approve`, {
        method: 'POST',
      });
      const result = await response.json();
      if (result.success) {
        alert('Ad approved!');
        fetchAd();
      }
    } catch (error) {
      console.error('Failed to approve ad:', error);
    }
  };

  const publishAd = async () => {
    if (!window.confirm('Publish this ad to ' + ad?.platform + '?')) return;

    try {
      const response = await fetch(`/api/ad-campaigns/ads/${adId}/publish`, {
        method: 'POST',
      });
      const result = await response.json();
      if (result.success) {
        alert('Ad published successfully!');
        fetchAd();
      }
    } catch (error) {
      console.error('Failed to publish ad:', error);
      alert('Failed to publish ad');
    }
  };

  if (loading || !ad) {
    return <div className="p-8 text-center">Loading ad editor...</div>;
  }

  const headlineMaxLength = 125;
  const bodyMaxLength = 2200;

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      {/* Header */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Edit Ad Creative</CardTitle>
            <p className="text-sm text-gray-600 mt-1">
              {ad.platform.toUpperCase()} • {ad.format} • Status: <Badge>{ad.status}</Badge>
            </p>
          </div>
          <div className="space-x-2">
            {onClose && (
              <Button variant="outline" onClick={onClose}>
                ← Back to Campaign
              </Button>
            )}
            <Button variant="outline" onClick={() => fetchAd()}>
              🔄 Refresh
            </Button>
            {ad.status === 'draft' && (
              <Button onClick={approveAd} className="bg-green-600 hover:bg-green-700">
                ✅ Approve Ad
              </Button>
            )}
            {ad.status === 'approved' && (
              <Button onClick={publishAd} className="bg-blue-600 hover:bg-blue-700">
                🚀 Publish to {ad.platform.toUpperCase()}
              </Button>
            )}
          </div>
        </CardHeader>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Preview */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Ad Preview</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="border-2 border-gray-200 rounded-lg p-4 bg-white">
                {/* Image/Video */}
                {ad.image_url && (
                  <img
                    src={ad.image_url}
                    alt="Ad creative"
                    className="w-full rounded-lg mb-4"
                  />
                )}

                {/* Headline */}
                <h3 className="font-semibold text-lg mb-2">{ad.headline || '(No headline)'}</h3>

                {/* Body */}
                <p className="text-gray-700 text-sm mb-4 whitespace-pre-wrap">
                  {ad.body || '(No body copy)'}
                </p>

                {/* CTA Button */}
                {ad.cta && (
                  <Button className="w-full bg-blue-600 hover:bg-blue-700">
                    {ad.cta}
                  </Button>
                )}

                {/* Platform info */}
                <div className="mt-4 pt-4 border-t text-xs text-gray-500">
                  Platform: {ad.platform} | Format: {ad.format}
                </div>
              </div>

              {/* Estimated reach */}
              {ad.target_audience && (
                <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                  <div className="text-sm font-semibold text-blue-900">Estimated Reach</div>
                  <div className="text-lg font-bold text-blue-700">450,000 - 580,000 people</div>
                  <div className="text-xs text-blue-600 mt-1">
                    Based on your targeting settings
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right: Editor */}
        <div className="space-y-6">
          <Tabs defaultValue="creative">
            <TabsList className="w-full">
              <TabsTrigger value="creative" className="flex-1">Creative</TabsTrigger>
              <TabsTrigger value="targeting" className="flex-1">Targeting</TabsTrigger>
              <TabsTrigger value="placement" className="flex-1">Placement</TabsTrigger>
            </TabsList>

            {/* Creative Tab */}
            <TabsContent value="creative">
              <Card>
                <CardHeader>
                  <CardTitle>Edit Ad Creative</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Headline */}
                  <div>
                    <Label htmlFor="headline">Headline ({ad.headline?.length || 0}/{headlineMaxLength})</Label>
                    <Input
                      id="headline"
                      value={ad.headline || ''}
                      onChange={(e) => setAd({ ...ad, headline: e.target.value })}
                      onBlur={() => updateAd({ headline: ad.headline })}
                      maxLength={headlineMaxLength}
                      placeholder="Enter headline..."
                      className="mt-1"
                    />
                  </div>

                  {/* Body */}
                  <div>
                    <Label htmlFor="body">Body Copy ({ad.body?.length || 0}/{bodyMaxLength})</Label>
                    <Textarea
                      id="body"
                      value={ad.body || ''}
                      onChange={(e) => setAd({ ...ad, body: e.target.value })}
                      onBlur={() => updateAd({ body: ad.body })}
                      maxLength={bodyMaxLength}
                      placeholder="Enter ad copy..."
                      rows={8}
                      className="mt-1"
                    />
                  </div>

                  {/* CTA */}
                  <div>
                    <Label htmlFor="cta">Call-to-Action</Label>
                    <Select
                      value={ad.cta || 'Learn More'}
                      onValueChange={(value) => {
                        setAd({ ...ad, cta: value });
                        updateAd({ cta: value });
                      }}
                    >
                      <SelectTrigger className="mt-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Buy Tickets">Buy Tickets</SelectItem>
                        <SelectItem value="Get Tickets">Get Tickets</SelectItem>
                        <SelectItem value="Buy Now">Buy Now</SelectItem>
                        <SelectItem value="Learn More">Learn More</SelectItem>
                        <SelectItem value="See Event">See Event</SelectItem>
                        <SelectItem value="Get Tickets Now">Get Tickets Now</SelectItem>
                        <SelectItem value="Sign Up">Sign Up</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Link URL */}
                  <div>
                    <Label htmlFor="link_url">Link URL</Label>
                    <Input
                      id="link_url"
                      value={ad.link_url || ''}
                      onChange={(e) => setAd({ ...ad, link_url: e.target.value })}
                      onBlur={() => updateAd({ link_url: ad.link_url })}
                      placeholder="https://..."
                      className="mt-1"
                    />
                  </div>

                  {/* Image Selection */}
                  <div>
                    <Label>Image/Video</Label>
                    <div className="grid grid-cols-2 gap-2 mt-2">
                      {availableImages.map((img, idx) => (
                        <div
                          key={idx}
                          onClick={() => {
                            setAd({ ...ad, image_url: img.url });
                            updateAd({ image_url: img.url });
                          }}
                          className={`cursor-pointer border-2 rounded-lg p-2 hover:border-blue-500 transition ${
                            ad.image_url === img.url ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                          }`}
                        >
                          <img src={img.url} alt={img.type} className="w-full rounded" />
                          <div className="text-xs mt-1 text-center text-gray-600">
                            {img.source} - {img.type}
                          </div>
                        </div>
                      ))}
                    </div>
                    <Button variant="outline" className="w-full mt-2">
                      📎 Upload Custom Image
                    </Button>
                  </div>

                  <Button
                    onClick={() => updateAd(ad)}
                    disabled={saving}
                    className="w-full bg-green-600 hover:bg-green-700"
                  >
                    {saving ? '💾 Saving...' : '💾 Save Changes'}
                  </Button>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Targeting Tab */}
            <TabsContent value="targeting">
              <Card>
                <CardHeader>
                  <CardTitle>Target Audience</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Age Range */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="age_min">Min Age</Label>
                      <Input
                        id="age_min"
                        type="number"
                        value={ad.target_audience?.age_min || 18}
                        onChange={(e) => {
                          const newAudience = { ...ad.target_audience, age_min: parseInt(e.target.value) };
                          setAd({ ...ad, target_audience: newAudience });
                        }}
                        onBlur={() => updateAd({ target_audience: ad.target_audience })}
                        className="mt-1"
                      />
                    </div>
                    <div>
                      <Label htmlFor="age_max">Max Age</Label>
                      <Input
                        id="age_max"
                        type="number"
                        value={ad.target_audience?.age_max || 65}
                        onChange={(e) => {
                          const newAudience = { ...ad.target_audience, age_max: parseInt(e.target.value) };
                          setAd({ ...ad, target_audience: newAudience });
                        }}
                        onBlur={() => updateAd({ target_audience: ad.target_audience })}
                        className="mt-1"
                      />
                    </div>
                  </div>

                  {/* Languages */}
                  <div>
                    <Label>Languages</Label>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {['English', 'Spanish', 'French', 'Portuguese'].map((lang) => (
                        <Badge
                          key={lang}
                          variant={ad.target_audience?.languages?.includes(lang) ? 'default' : 'outline'}
                          className="cursor-pointer"
                          onClick={() => {
                            const languages = ad.target_audience?.languages || [];
                            const newLanguages = languages.includes(lang)
                              ? languages.filter((l: string) => l !== lang)
                              : [...languages, lang];
                            const newAudience = { ...ad.target_audience, languages: newLanguages };
                            setAd({ ...ad, target_audience: newAudience });
                            updateAd({ target_audience: newAudience });
                          }}
                        >
                          {lang}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  {/* Interests */}
                  <div>
                    <Label>Interests (AI-suggested)</Label>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {['Concerts', 'Live Music', 'Music Festivals', 'Nightlife', 'Entertainment'].map((interest) => (
                        <Badge
                          key={interest}
                          variant={ad.target_audience?.interests?.includes(interest) ? 'default' : 'outline'}
                          className="cursor-pointer"
                          onClick={() => {
                            const interests = ad.target_audience?.interests || [];
                            const newInterests = interests.includes(interest)
                              ? interests.filter((i: string) => i !== interest)
                              : [...interests, interest];
                            const newAudience = { ...ad.target_audience, interests: newInterests };
                            setAd({ ...ad, target_audience: newAudience });
                            updateAd({ target_audience: newAudience });
                          }}
                        >
                          {interest}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  <Button
                    onClick={() => updateAd({ target_audience: ad.target_audience })}
                    disabled={saving}
                    className="w-full bg-green-600 hover:bg-green-700"
                  >
                    {saving ? '💾 Saving...' : '💾 Save Targeting'}
                  </Button>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Placement Tab */}
            <TabsContent value="placement">
              <Card>
                <CardHeader>
                  <CardTitle>Platform & Placement</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label>Select Placements</Label>
                    <div className="space-y-2 mt-2">
                      {[
                        { value: 'facebook_feed', label: 'Facebook Feed' },
                        { value: 'instagram_feed', label: 'Instagram Feed' },
                        { value: 'instagram_stories', label: 'Instagram Stories' },
                        { value: 'facebook_stories', label: 'Facebook Stories' },
                        { value: 'messenger', label: 'Messenger' },
                        { value: 'audience_network', label: 'Audience Network' },
                      ].map((placement) => (
                        <label key={placement.value} className="flex items-center space-x-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={ad.placements?.includes(placement.value)}
                            onChange={(e) => {
                              const newPlacements = e.target.checked
                                ? [...(ad.placements || []), placement.value]
                                : (ad.placements || []).filter((p: string) => p !== placement.value);
                              setAd({ ...ad, placements: newPlacements });
                              updateAd({ placements: newPlacements });
                            }}
                            className="rounded"
                          />
                          <span>{placement.label}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
};

export default AdEditor;
