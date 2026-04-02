/**
 * Ad Campaign Dashboard
 * Main view for managing all ad campaigns for an event
 */

import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

interface Campaign {
  id: number;
  name: string;
  platform: string;
  campaign_type: string;
  status: string;
  budget_total: number;
  spend_total: number;
  ad_count: number;
  start_date: string;
  end_date: string;
}

interface AdCampaignDashboardProps {
  eventId: number;
}

export const AdCampaignDashboard: React.FC<AdCampaignDashboardProps> = ({ eventId }) => {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCampaign, setSelectedCampaign] = useState<Campaign | null>(null);

  useEffect(() => {
    fetchCampaigns();
  }, [eventId]);

  const fetchCampaigns = async () => {
    try {
      const response = await fetch(`/api/ad-campaigns/event/${eventId}`);
      const data = await response.json();
      setCampaigns(data);
    } catch (error) {
      console.error('Failed to fetch campaigns:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateCampaigns = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/ad-campaigns/generate/${eventId}`, {
        method: 'POST',
      });
      const result = await response.json();

      if (result.success) {
        alert(`Created ${result.campaigns_created} campaigns with ${result.ads_created} ads!`);
        fetchCampaigns();
      }
    } catch (error) {
      console.error('Failed to generate campaigns:', error);
      alert('Error generating campaigns');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'draft': return 'bg-gray-500';
      case 'approved': return 'bg-blue-500';
      case 'active': return 'bg-green-500';
      case 'paused': return 'bg-yellow-500';
      case 'completed': return 'bg-purple-500';
      default: return 'bg-gray-500';
    }
  };

  const getPlatformIcon = (platform: string) => {
    switch (platform) {
      case 'meta': return '📱';
      case 'google': return '🔍';
      case 'email': return '📧';
      case 'social_organic': return '🌐';
      default: return '📊';
    }
  };

  const totalBudget = campaigns.reduce((sum, c) => sum + c.budget_total, 0);
  const totalSpend = campaigns.reduce((sum, c) => sum + c.spend_total, 0);
  const totalAds = campaigns.reduce((sum, c) => sum + c.ad_count, 0);

  const draftAds = campaigns.filter(c => c.status === 'draft').reduce((sum, c) => sum + c.ad_count, 0);
  const approvedAds = campaigns.filter(c => c.status === 'approved').reduce((sum, c) => sum + c.ad_count, 0);
  const activeAds = campaigns.filter(c => c.status === 'active').reduce((sum, c) => sum + c.ad_count, 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading campaigns...</p>
        </div>
      </div>
    );
  }

  if (campaigns.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Ad Campaigns</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <div className="text-6xl mb-4">🎯</div>
            <h3 className="text-xl font-semibold mb-2">No Campaigns Yet</h3>
            <p className="text-gray-600 mb-6">
              Generate ad campaigns automatically from your event research
            </p>
            <Button onClick={generateCampaigns} className="bg-blue-600 hover:bg-blue-700">
              🤖 Generate Campaigns Automatically
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Overview Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">{campaigns.length}</div>
            <div className="text-sm text-gray-600">Total Campaigns</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">{totalAds}</div>
            <div className="text-sm text-gray-600">Total Ads</div>
            <div className="text-xs text-gray-500 mt-1">
              📝 {draftAds} draft • ✅ {approvedAds} approved • 🚀 {activeAds} active
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">${(totalBudget / 100).toFixed(0)}</div>
            <div className="text-sm text-gray-600">Total Budget</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">${(totalSpend / 100).toFixed(0)}</div>
            <div className="text-sm text-gray-600">Total Spend</div>
            <div className="text-xs text-gray-500 mt-1">
              {totalBudget > 0 ? `${((totalSpend / totalBudget) * 100).toFixed(1)}% of budget` : ''}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Campaigns by Platform */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Campaign Manager</CardTitle>
          <div className="space-x-2">
            <Button variant="outline" onClick={fetchCampaigns}>
              🔄 Refresh
            </Button>
            <Button variant="outline" onClick={() => alert('Bulk operations coming soon')}>
              ⚙️ Bulk Actions
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="all">
            <TabsList>
              <TabsTrigger value="all">All ({campaigns.length})</TabsTrigger>
              <TabsTrigger value="meta">Meta Ads ({campaigns.filter(c => c.platform === 'meta').length})</TabsTrigger>
              <TabsTrigger value="google">Google Ads ({campaigns.filter(c => c.platform === 'google').length})</TabsTrigger>
              <TabsTrigger value="email">Email ({campaigns.filter(c => c.platform === 'email').length})</TabsTrigger>
            </TabsList>

            <TabsContent value="all" className="space-y-4 mt-4">
              {campaigns.map((campaign) => (
                <CampaignCard
                  key={campaign.id}
                  campaign={campaign}
                  onSelect={() => setSelectedCampaign(campaign)}
                  getStatusColor={getStatusColor}
                  getPlatformIcon={getPlatformIcon}
                />
              ))}
            </TabsContent>

            <TabsContent value="meta" className="space-y-4 mt-4">
              {campaigns.filter(c => c.platform === 'meta').map((campaign) => (
                <CampaignCard
                  key={campaign.id}
                  campaign={campaign}
                  onSelect={() => setSelectedCampaign(campaign)}
                  getStatusColor={getStatusColor}
                  getPlatformIcon={getPlatformIcon}
                />
              ))}
            </TabsContent>

            <TabsContent value="google" className="space-y-4 mt-4">
              {campaigns.filter(c => c.platform === 'google').map((campaign) => (
                <CampaignCard
                  key={campaign.id}
                  campaign={campaign}
                  onSelect={() => setSelectedCampaign(campaign)}
                  getStatusColor={getStatusColor}
                  getPlatformIcon={getPlatformIcon}
                />
              ))}
            </TabsContent>

            <TabsContent value="email" className="space-y-4 mt-4">
              {campaigns.filter(c => c.platform === 'email').map((campaign) => (
                <CampaignCard
                  key={campaign.id}
                  campaign={campaign}
                  onSelect={() => setSelectedCampaign(campaign)}
                  getStatusColor={getStatusColor}
                  getPlatformIcon={getPlatformIcon}
                />
              ))}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
};

interface CampaignCardProps {
  campaign: Campaign;
  onSelect: () => void;
  getStatusColor: (status: string) => string;
  getPlatformIcon: (platform: string) => string;
}

const CampaignCard: React.FC<CampaignCardProps> = ({ campaign, onSelect, getStatusColor, getPlatformIcon }) => {
  return (
    <Card className="hover:shadow-lg transition-shadow">
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4 flex-1">
            <div className="text-4xl">{getPlatformIcon(campaign.platform)}</div>
            <div className="flex-1">
              <div className="flex items-center space-x-2 mb-1">
                <h3 className="font-semibold text-lg">{campaign.name}</h3>
                <Badge className={getStatusColor(campaign.status)}>
                  {campaign.status.toUpperCase()}
                </Badge>
              </div>
              <div className="text-sm text-gray-600">
                {campaign.platform.toUpperCase()} • {campaign.campaign_type} • {campaign.ad_count} ads
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Budget: ${(campaign.budget_total / 100).toFixed(0)} |
                Spend: ${(campaign.spend_total / 100).toFixed(0)} |
                Dates: {new Date(campaign.start_date).toLocaleDateString()} - {new Date(campaign.end_date).toLocaleDateString()}
              </div>
            </div>
          </div>

          <div className="space-x-2">
            <Button variant="outline" size="sm" onClick={onSelect}>
              👁️ View {campaign.ad_count} Ads
            </Button>
            <Button variant="outline" size="sm">
              ✏️ Edit Campaign
            </Button>
            {campaign.status === 'draft' && (
              <Button size="sm" className="bg-green-600 hover:bg-green-700">
                ✅ Approve All
              </Button>
            )}
            {campaign.status === 'approved' && (
              <Button size="sm" className="bg-blue-600 hover:bg-blue-700">
                🚀 Publish All
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default AdCampaignDashboard;
