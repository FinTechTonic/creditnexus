/**
 * Data Input Form Component
 * 
 * Provides a structured form for inputting CDM data with sections for:
 * - Parties (Borrower, Lenders, Agents)
 * - Facilities (name, amount, currency, maturity, interest)
 * - Agreement details (date, governing law)
 * - ESG sections (if sustainability-linked)
 */

import { useState } from 'react';
import { Plus, Trash2, Building2, DollarSign, Calendar, Leaf } from 'lucide-react';

interface Party {
  name: string;
  lei?: string;
  role: string;
}

interface Facility {
  facility_name: string;
  commitment_amount: {
    amount: number;
    currency: string;
  };
  maturity_date?: string;
  interest_terms?: {
    rate_option: {
      benchmark: string;
      spread_bps: number;
    };
    payment_frequency?: {
      period: string;
      period_multiplier: number;
    };
  };
  spread_bps?: number; // Direct access for convenience
}

interface CreditAgreementData {
  parties?: Party[];
  facilities?: Facility[];
  agreement_date?: string;
  governing_law?: string;
  deal_id?: string;
  sustainability_linked?: boolean;
  esg_kpi_targets?: Array<{
    kpi_type: string;
    target_value: number;
    unit: string;
    margin_adjustment_bps: number;
  }>;
}

interface DataInputFormProps {
  data: CreditAgreementData;
  onDataChange: (data: CreditAgreementData) => void;
}

export function DataInputForm({ data, onDataChange }: DataInputFormProps) {
  const [localData, setLocalData] = useState<CreditAgreementData>(data || {});

  const updateData = (updates: Partial<CreditAgreementData>) => {
    const newData = { ...localData, ...updates };
    setLocalData(newData);
    onDataChange(newData);
  };

  const addParty = () => {
    const parties = localData.parties || [];
    updateData({
      parties: [...parties, { name: '', role: 'Borrower', lei: '' }],
    });
  };

  const removeParty = (index: number) => {
    const parties = localData.parties || [];
    updateData({
      parties: parties.filter((_, i) => i !== index),
    });
  };

  const updateParty = (index: number, updates: Partial<Party>) => {
    const parties = localData.parties || [];
    updateData({
      parties: parties.map((p, i) => i === index ? { ...p, ...updates } : p),
    });
  };

  const addFacility = () => {
    const facilities = localData.facilities || [];
    updateData({
      facilities: [...facilities, {
        facility_name: '',
        commitment_amount: { amount: 0, currency: 'USD' },
        interest_terms: {
          rate_option: { benchmark: 'SOFR', spread_bps: 0 },
          payment_frequency: { period: 'Month', period_multiplier: 1 },
        },
      }],
    });
  };

  const removeFacility = (index: number) => {
    const facilities = localData.facilities || [];
    updateData({
      facilities: facilities.filter((_, i) => i !== index),
    });
  };

  const updateFacility = (index: number, updates: Partial<Facility>) => {
    const facilities = localData.facilities || [];
    updateData({
      facilities: facilities.map((f, i) => i === index ? { ...f, ...updates } : f),
    });
  };

  return (
    <div className="space-y-6">
      {/* Agreement Details */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h3 className="text-md font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Calendar className="h-5 w-5 text-blue-600" />
          Agreement Details
        </h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Agreement Date
            </label>
            <input
              type="date"
              value={localData.agreement_date || ''}
              onChange={(e) => updateData({ agreement_date: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Governing Law
            </label>
            <select
              value={localData.governing_law || ''}
              onChange={(e) => updateData({ governing_law: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
            >
              <option value="">Select...</option>
              <option value="English">English</option>
              <option value="NY">New York</option>
              <option value="Delaware">Delaware</option>
              <option value="California">California</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Deal ID
            </label>
            <input
              type="text"
              value={localData.deal_id || ''}
              onChange={(e) => updateData({ deal_id: e.target.value })}
              placeholder="DEAL_2024_001"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Sustainability Linked
            </label>
            <select
              value={localData.sustainability_linked ? 'yes' : 'no'}
              onChange={(e) => updateData({ sustainability_linked: e.target.value === 'yes' })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
            >
              <option value="no">No</option>
              <option value="yes">Yes</option>
            </select>
          </div>
        </div>
      </div>

      {/* Parties */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-md font-semibold text-gray-900 flex items-center gap-2">
            <Building2 className="h-5 w-5 text-blue-600" />
            Parties
          </h3>
          <button
            onClick={addParty}
            className="flex items-center gap-1 px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
          >
            <Plus className="h-4 w-4" />
            Add Party
          </button>
        </div>
        <div className="space-y-3">
          {localData.parties?.map((party, index) => (
            <div key={index} className="p-3 bg-gray-50 rounded-lg border border-gray-200">
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Name
                  </label>
                  <input
                    type="text"
                    value={party.name}
                    onChange={(e) => updateParty(index, { name: e.target.value })}
                    placeholder="Party Name"
                    className="w-full px-2 py-1.5 border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Role
                  </label>
                  <select
                    value={party.role}
                    onChange={(e) => updateParty(index, { role: e.target.value })}
                    className="w-full px-2 py-1.5 border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500 text-sm"
                  >
                    <option value="Borrower">Borrower</option>
                    <option value="Lender">Lender</option>
                    <option value="Agent">Agent</option>
                    <option value="Guarantor">Guarantor</option>
                  </select>
                </div>
                <div className="flex items-end gap-2">
                  <div className="flex-1">
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      LEI (Optional)
                    </label>
                    <input
                      type="text"
                      value={party.lei || ''}
                      onChange={(e) => updateParty(index, { lei: e.target.value })}
                      placeholder="LEI"
                      className="w-full px-2 py-1.5 border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500 text-sm"
                    />
                  </div>
                  <button
                    onClick={() => removeParty(index)}
                    className="p-1.5 text-red-600 hover:bg-red-50 rounded"
                    title="Remove party"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
          {(!localData.parties || localData.parties.length === 0) && (
            <div className="text-center py-4 text-gray-500 text-sm">
              No parties added. Click "Add Party" to get started.
            </div>
          )}
        </div>
      </div>

      {/* Facilities */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-md font-semibold text-gray-900 flex items-center gap-2">
            <DollarSign className="h-5 w-5 text-blue-600" />
            Facilities
          </h3>
          <button
            onClick={addFacility}
            className="flex items-center gap-1 px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
          >
            <Plus className="h-4 w-4" />
            Add Facility
          </button>
        </div>
        <div className="space-y-4">
          {localData.facilities?.map((facility, index) => (
            <div key={index} className="p-4 bg-gray-50 rounded-lg border border-gray-200">
              <div className="grid grid-cols-2 gap-4 mb-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Facility Name
                  </label>
                  <input
                    type="text"
                    value={facility.facility_name}
                    onChange={(e) => updateFacility(index, { facility_name: e.target.value })}
                    placeholder="Revolving Credit Facility"
                    className="w-full px-2 py-1.5 border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Maturity Date
                  </label>
                  <input
                    type="date"
                    value={facility.maturity_date || ''}
                    onChange={(e) => updateFacility(index, { maturity_date: e.target.value })}
                    className="w-full px-2 py-1.5 border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500 text-sm"
                  />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3 mb-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Amount
                  </label>
                  <input
                    type="number"
                    value={facility.commitment_amount?.amount || 0}
                    onChange={(e) => updateFacility(index, {
                      commitment_amount: {
                        ...facility.commitment_amount,
                        amount: parseFloat(e.target.value) || 0,
                      },
                    })}
                    className="w-full px-2 py-1.5 border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Currency
                  </label>
                  <select
                    value={facility.commitment_amount?.currency || 'USD'}
                    onChange={(e) => updateFacility(index, {
                      commitment_amount: {
                        ...facility.commitment_amount,
                        currency: e.target.value,
                      },
                    })}
                    className="w-full px-2 py-1.5 border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500 text-sm"
                  >
                    <option value="USD">USD</option>
                    <option value="EUR">EUR</option>
                    <option value="GBP">GBP</option>
                    <option value="JPY">JPY</option>
                  </select>
                </div>
                <div className="flex items-end">
                  <button
                    onClick={() => removeFacility(index)}
                    className="p-1.5 text-red-600 hover:bg-red-50 rounded"
                    title="Remove facility"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
              {facility.interest_terms && (
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      Benchmark
                    </label>
                    <select
                      value={facility.interest_terms.rate_option?.benchmark || 'SOFR'}
                      onChange={(e) => {
                        if (!facility.interest_terms) return;
                        updateFacility(index, {
                          interest_terms: {
                            ...facility.interest_terms,
                            rate_option: {
                              benchmark: e.target.value,
                              spread_bps: facility.interest_terms.rate_option?.spread_bps || 0,
                            },
                          },
                        });
                      }}
                      className="w-full px-2 py-1.5 border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500 text-sm"
                    >
                      <option value="SOFR">SOFR</option>
                      <option value="LIBOR">LIBOR</option>
                      <option value="EURIBOR">EURIBOR</option>
                      <option value="SONIA">SONIA</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      Spread (bps)
                    </label>
                    <input
                      type="number"
                      value={facility.interest_terms.rate_option?.spread_bps || 0}
                      onChange={(e) => {
                        if (!facility.interest_terms) return;
                        updateFacility(index, {
                          interest_terms: {
                            ...facility.interest_terms,
                            rate_option: {
                              benchmark: facility.interest_terms.rate_option?.benchmark || 'SOFR',
                              spread_bps: parseInt(e.target.value) || 0,
                            },
                          },
                        });
                      }}
                      className="w-full px-2 py-1.5 border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500 text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      Payment Frequency
                    </label>
                    <select
                      value={`${facility.interest_terms.payment_frequency?.period || 'Month'}_${facility.interest_terms.payment_frequency?.period_multiplier || 1}`}
                      onChange={(e) => {
                        const [period, multiplier] = e.target.value.split('_');
                        updateFacility(index, {
                          interest_terms: {
                            rate_option: facility.interest_terms?.rate_option || {
                              benchmark: 'SOFR',
                              spread_bps: facility.spread_bps || 200
                            },
                            payment_frequency: {
                              period,
                              period_multiplier: parseInt(multiplier),
                            },
                          },
                        });
                      }}
                      className="w-full px-2 py-1.5 border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500 text-sm"
                    >
                      <option value="Month_1">Monthly</option>
                      <option value="Month_3">Quarterly</option>
                      <option value="Month_6">Semi-annually</option>
                      <option value="Year_1">Annually</option>
                    </select>
                  </div>
                </div>
              )}
            </div>
          ))}
          {(!localData.facilities || localData.facilities.length === 0) && (
            <div className="text-center py-4 text-gray-500 text-sm">
              No facilities added. Click "Add Facility" to get started.
            </div>
          )}
        </div>
      </div>

      {/* ESG Section */}
      {localData.sustainability_linked && (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h3 className="text-md font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Leaf className="h-5 w-5 text-green-600" />
            ESG KPI Targets
          </h3>
          <div className="text-sm text-gray-600">
            ESG KPI targets can be added here. This section will be expanded with
            full ESG target management in a future update.
          </div>
        </div>
      )}
    </div>
  );
}
















