/**
 * Accounting Document Display Component
 * 
 * Displays extracted accounting document data with validation indicators
 * for Balance Sheets, Income Statements, Cash Flow Statements, and Tax Returns.
 */

import { Card, CardContent } from '@/components/ui/card';
import { CheckCircle2, AlertCircle, XCircle } from 'lucide-react';

interface AccountingDocumentDisplayProps {
  data: any; // Accounting document data (BalanceSheet, IncomeStatement, etc.)
  extractionStatus?: string;
}

export function AccountingDocumentDisplay({ data, extractionStatus }: AccountingDocumentDisplayProps) {
  if (!data) return null;

  const documentType = data.document_type || 'unknown';
  const isBalanced = extractionStatus === 'success';
  const hasWarnings = extractionStatus === 'partial_data_missing';

  const formatMoney = (money: any) => {
    if (!money) return 'N/A';
    const amount = typeof money === 'object' ? money.amount : money;
    const currency = typeof money === 'object' ? money.currency : 'USD';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency || 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return 'N/A';
    try {
      return new Date(dateStr).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  const renderValidationStatus = () => {
    if (isBalanced) {
      return (
        <div className="flex items-center gap-2 text-emerald-400">
          <CheckCircle2 className="h-4 w-4" />
          <span className="text-sm font-medium">Validated - All equations balance</span>
        </div>
      );
    } else if (hasWarnings) {
      return (
        <div className="flex items-center gap-2 text-yellow-400">
          <AlertCircle className="h-4 w-4" />
          <span className="text-sm font-medium">Partial Data - Some validations failed</span>
        </div>
      );
    } else {
      return (
        <div className="flex items-center gap-2 text-red-400">
          <XCircle className="h-4 w-4" />
          <span className="text-sm font-medium">Validation Failed</span>
        </div>
      );
    }
  };

  const renderBalanceSheet = () => {
    if (documentType !== 'balance_sheet') return null;

    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Balance Sheet</h3>
          {renderValidationStatus()}
        </div>

        {data.reporting_period && (
          <div className="text-sm text-slate-400">
            Period: {formatDate(data.reporting_period.start_date)} - {formatDate(data.reporting_period.end_date)}
            {data.reporting_period.fiscal_year && ` (FY ${data.reporting_period.fiscal_year})`}
          </div>
        )}

        <div className="grid md:grid-cols-2 gap-6">
          {/* Assets */}
          <Card className="border-slate-700 bg-slate-800/50">
            <CardContent className="p-4">
              <h4 className="font-semibold mb-4 text-emerald-400">Assets</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-400">Cash & Equivalents:</span>
                  <span className="font-medium">{formatMoney(data.cash_and_equivalents)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Accounts Receivable:</span>
                  <span className="font-medium">{formatMoney(data.accounts_receivable)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Inventory:</span>
                  <span className="font-medium">{formatMoney(data.inventory)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Prepaid Expenses:</span>
                  <span className="font-medium">{formatMoney(data.prepaid_expenses)}</span>
                </div>
                <div className="border-t border-slate-700 pt-2 mt-2">
                  <div className="flex justify-between font-semibold">
                    <span>Total Current Assets:</span>
                    <span className="text-emerald-400">{formatMoney(data.total_current_assets)}</span>
                  </div>
                </div>
                <div className="flex justify-between mt-4">
                  <span className="text-slate-400">Property, Plant & Equipment:</span>
                  <span className="font-medium">{formatMoney(data.property_plant_equipment)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Intangible Assets:</span>
                  <span className="font-medium">{formatMoney(data.intangible_assets)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Investments:</span>
                  <span className="font-medium">{formatMoney(data.investments)}</span>
                </div>
                <div className="border-t border-slate-700 pt-2 mt-2">
                  <div className="flex justify-between font-semibold">
                    <span>Total Non-Current Assets:</span>
                    <span className="text-emerald-400">{formatMoney(data.total_non_current_assets)}</span>
                  </div>
                </div>
                <div className="border-t-2 border-emerald-500 pt-2 mt-4">
                  <div className="flex justify-between font-bold text-lg">
                    <span>Total Assets:</span>
                    <span className="text-emerald-400">{formatMoney(data.total_assets)}</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Liabilities & Equity */}
          <Card className="border-slate-700 bg-slate-800/50">
            <CardContent className="p-4">
              <h4 className="font-semibold mb-4 text-red-400">Liabilities</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-400">Accounts Payable:</span>
                  <span className="font-medium">{formatMoney(data.accounts_payable)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Short-term Debt:</span>
                  <span className="font-medium">{formatMoney(data.short_term_debt)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Accrued Expenses:</span>
                  <span className="font-medium">{formatMoney(data.accrued_expenses)}</span>
                </div>
                <div className="border-t border-slate-700 pt-2 mt-2">
                  <div className="flex justify-between font-semibold">
                    <span>Total Current Liabilities:</span>
                    <span className="text-red-400">{formatMoney(data.total_current_liabilities)}</span>
                  </div>
                </div>
                <div className="flex justify-between mt-4">
                  <span className="text-slate-400">Long-term Debt:</span>
                  <span className="font-medium">{formatMoney(data.long_term_debt)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Deferred Tax Liabilities:</span>
                  <span className="font-medium">{formatMoney(data.deferred_tax_liabilities)}</span>
                </div>
                <div className="border-t border-slate-700 pt-2 mt-2">
                  <div className="flex justify-between font-semibold">
                    <span>Total Non-Current Liabilities:</span>
                    <span className="text-red-400">{formatMoney(data.total_non_current_liabilities)}</span>
                  </div>
                </div>
                <div className="border-t-2 border-red-500 pt-2 mt-4">
                  <div className="flex justify-between font-bold text-lg">
                    <span>Total Liabilities:</span>
                    <span className="text-red-400">{formatMoney(data.total_liabilities)}</span>
                  </div>
                </div>
              </div>

              <h4 className="font-semibold mb-4 mt-6 text-blue-400">Equity</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-400">Common Stock:</span>
                  <span className="font-medium">{formatMoney(data.common_stock)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Retained Earnings:</span>
                  <span className="font-medium">{formatMoney(data.retained_earnings)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Additional Paid-in Capital:</span>
                  <span className="font-medium">{formatMoney(data.additional_paid_in_capital)}</span>
                </div>
                <div className="border-t-2 border-blue-500 pt-2 mt-4">
                  <div className="flex justify-between font-bold text-lg">
                    <span>Total Equity:</span>
                    <span className="text-blue-400">{formatMoney(data.total_equity)}</span>
                  </div>
                </div>
              </div>

              {/* Balance Validation */}
              {data.total_assets && data.total_liabilities && data.total_equity && (
                <div className="mt-4 pt-4 border-t border-slate-700">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-400">Liabilities + Equity:</span>
                    <span className="font-semibold">
                      {formatMoney({
                        amount: (data.total_liabilities?.amount || 0) + (data.total_equity?.amount || 0),
                        currency: data.total_assets.currency
                      })}
                    </span>
                  </div>
                  <div className="flex items-center justify-between mt-2">
                    <span className="text-sm text-slate-400">Total Assets:</span>
                    <span className="font-semibold">{formatMoney(data.total_assets)}</span>
                  </div>
                  {Math.abs((data.total_assets?.amount || 0) - ((data.total_liabilities?.amount || 0) + (data.total_equity?.amount || 0))) < 0.01 ? (
                    <div className="mt-2 flex items-center gap-2 text-emerald-400 text-sm">
                      <CheckCircle2 className="h-4 w-4" />
                      <span>Balance Sheet balances correctly</span>
                    </div>
                  ) : (
                    <div className="mt-2 flex items-center gap-2 text-red-400 text-sm">
                      <XCircle className="h-4 w-4" />
                      <span>Balance Sheet does not balance</span>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    );
  };

  const renderIncomeStatement = () => {
    if (documentType !== 'income_statement') return null;

    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Income Statement</h3>
          {renderValidationStatus()}
        </div>

        {data.reporting_period && (
          <div className="text-sm text-slate-400">
            Period: {formatDate(data.reporting_period.start_date)} - {formatDate(data.reporting_period.end_date)}
            {data.reporting_period.fiscal_year && ` (FY ${data.reporting_period.fiscal_year})`}
          </div>
        )}

        <Card className="border-slate-700 bg-slate-800/50">
          <CardContent className="p-6">
            <div className="space-y-4">
              {/* Revenue */}
              <div>
                <h4 className="font-semibold mb-3 text-emerald-400">Revenue</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Gross Revenue:</span>
                    <span className="font-medium">{formatMoney(data.gross_revenue)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Net Revenue:</span>
                    <span className="font-medium">{formatMoney(data.net_revenue)}</span>
                  </div>
                  <div className="border-t border-slate-700 pt-2 mt-2">
                    <div className="flex justify-between font-semibold">
                      <span>Total Revenue:</span>
                      <span className="text-emerald-400">{formatMoney(data.total_revenue)}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Expenses */}
              <div>
                <h4 className="font-semibold mb-3 text-red-400">Expenses</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Cost of Goods Sold:</span>
                    <span className="font-medium">{formatMoney(data.cost_of_goods_sold)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">SG&A Expenses:</span>
                    <span className="font-medium">{formatMoney(data.selling_general_admin_expenses)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">R&D Expenses:</span>
                    <span className="font-medium">{formatMoney(data.research_development_expenses)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Depreciation & Amortization:</span>
                    <span className="font-medium">{formatMoney(data.depreciation_amortization)}</span>
                  </div>
                  <div className="border-t border-slate-700 pt-2 mt-2">
                    <div className="flex justify-between font-semibold">
                      <span>Total Operating Expenses:</span>
                      <span className="text-red-400">{formatMoney(data.total_operating_expenses)}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Net Income */}
              <div className="border-t-2 border-slate-700 pt-4">
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Operating Income:</span>
                    <span className="font-medium">{formatMoney(data.operating_income)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Interest Income:</span>
                    <span className="font-medium text-emerald-400">{formatMoney(data.interest_income)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Interest Expense:</span>
                    <span className="font-medium text-red-400">{formatMoney(data.interest_expense)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Tax Expense:</span>
                    <span className="font-medium text-red-400">{formatMoney(data.tax_expense)}</span>
                  </div>
                  <div className="border-t-2 border-slate-700 pt-2 mt-2">
                    <div className="flex justify-between font-bold text-lg">
                      <span>Net Income After Tax:</span>
                      <span className={data.net_income_after_tax?.amount >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                        {formatMoney(data.net_income_after_tax)}
                      </span>
                    </div>
                  </div>
                  {data.earnings_per_share && (
                    <div className="flex justify-between mt-2">
                      <span className="text-slate-400">Earnings Per Share:</span>
                      <span className="font-medium">${data.earnings_per_share.toFixed(2)}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  };

  const renderCashFlowStatement = () => {
    if (documentType !== 'cash_flow_statement') return null;

    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Cash Flow Statement</h3>
          {renderValidationStatus()}
        </div>

        {data.reporting_period && (
          <div className="text-sm text-slate-400">
            Period: {formatDate(data.reporting_period.start_date)} - {formatDate(data.reporting_period.end_date)}
            {data.reporting_period.fiscal_year && ` (FY ${data.reporting_period.fiscal_year})`}
          </div>
        )}

        <Card className="border-slate-700 bg-slate-800/50">
          <CardContent className="p-6">
            <div className="space-y-6">
              {/* Operating Activities */}
              <div>
                <h4 className="font-semibold mb-3 text-emerald-400">Operating Activities</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Net Income:</span>
                    <span className="font-medium">{formatMoney(data.net_income)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Depreciation & Amortization:</span>
                    <span className="font-medium">{formatMoney(data.depreciation_amortization)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Changes in Working Capital:</span>
                    <span className="font-medium">{formatMoney(data.changes_in_working_capital)}</span>
                  </div>
                  <div className="border-t border-slate-700 pt-2 mt-2">
                    <div className="flex justify-between font-semibold">
                      <span>Cash from Operations:</span>
                      <span className="text-emerald-400">{formatMoney(data.cash_from_operations)}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Investing Activities */}
              <div>
                <h4 className="font-semibold mb-3 text-blue-400">Investing Activities</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Capital Expenditures:</span>
                    <span className="font-medium text-red-400">{formatMoney(data.capital_expenditures)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Asset Sales:</span>
                    <span className="font-medium text-emerald-400">{formatMoney(data.asset_sales)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Investments Made:</span>
                    <span className="font-medium text-red-400">{formatMoney(data.investments_made)}</span>
                  </div>
                  <div className="border-t border-slate-700 pt-2 mt-2">
                    <div className="flex justify-between font-semibold">
                      <span>Cash from Investing:</span>
                      <span className="text-blue-400">{formatMoney(data.cash_from_investing)}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Financing Activities */}
              <div>
                <h4 className="font-semibold mb-3 text-purple-400">Financing Activities</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Debt Issuance/Repayment:</span>
                    <span className="font-medium">{formatMoney(data.debt_issuance_repayment)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Equity Issuance:</span>
                    <span className="font-medium text-emerald-400">{formatMoney(data.equity_issuance)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Dividends Paid:</span>
                    <span className="font-medium text-red-400">{formatMoney(data.dividends_paid)}</span>
                  </div>
                  <div className="border-t border-slate-700 pt-2 mt-2">
                    <div className="flex justify-between font-semibold">
                      <span>Cash from Financing:</span>
                      <span className="text-purple-400">{formatMoney(data.cash_from_financing)}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Net Change */}
              <div className="border-t-2 border-slate-700 pt-4">
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Beginning Cash Balance:</span>
                    <span className="font-medium">{formatMoney(data.beginning_cash_balance)}</span>
                  </div>
                  <div className="border-t border-slate-700 pt-2 mt-2">
                    <div className="flex justify-between font-semibold">
                      <span>Net Change in Cash:</span>
                      <span className={data.net_change_in_cash?.amount >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                        {formatMoney(data.net_change_in_cash)}
                      </span>
                    </div>
                  </div>
                  <div className="border-t-2 border-slate-700 pt-2 mt-2">
                    <div className="flex justify-between font-bold text-lg">
                      <span>Ending Cash Balance:</span>
                      <span className="text-emerald-400">{formatMoney(data.ending_cash_balance)}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  };

  const renderTaxReturn = () => {
    if (documentType !== 'tax_return') return null;

    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Tax Return</h3>
          {renderValidationStatus()}
        </div>

        {data.reporting_period && (
          <div className="text-sm text-slate-400">
            Tax Year: {data.reporting_period.fiscal_year || data.tax_year || 'N/A'}
            {data.filing_date && ` | Filing Date: ${formatDate(data.filing_date)}`}
            {data.filing_status && ` | Status: ${data.filing_status}`}
          </div>
        )}

        <div className="grid md:grid-cols-2 gap-6">
          <Card className="border-slate-700 bg-slate-800/50">
            <CardContent className="p-4">
              <h4 className="font-semibold mb-4 text-emerald-400">Income</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-400">Total Income:</span>
                  <span className="font-medium">{formatMoney(data.total_income)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Adjusted Gross Income:</span>
                  <span className="font-medium">{formatMoney(data.adjusted_gross_income)}</span>
                </div>
                <div className="border-t border-slate-700 pt-2 mt-2">
                  <div className="flex justify-between font-semibold">
                    <span>Taxable Income:</span>
                    <span className="text-emerald-400">{formatMoney(data.taxable_income)}</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-700 bg-slate-800/50">
            <CardContent className="p-4">
              <h4 className="font-semibold mb-4 text-red-400">Deductions & Tax</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-400">Standard Deduction:</span>
                  <span className="font-medium">{formatMoney(data.standard_deduction)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Itemized Deductions:</span>
                  <span className="font-medium">{formatMoney(data.itemized_deductions)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Business Deductions:</span>
                  <span className="font-medium">{formatMoney(data.business_deductions)}</span>
                </div>
                <div className="border-t border-slate-700 pt-2 mt-2">
                  <div className="flex justify-between font-semibold">
                    <span>Total Deductions:</span>
                    <span className="text-red-400">{formatMoney(data.total_deductions)}</span>
                  </div>
                </div>
                <div className="flex justify-between mt-4">
                  <span className="text-slate-400">Federal Tax Owed:</span>
                  <span className="font-medium text-red-400">{formatMoney(data.federal_tax_owed)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">State Tax Owed:</span>
                  <span className="font-medium text-red-400">{formatMoney(data.state_tax_owed)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Tax Credits:</span>
                  <span className="font-medium text-emerald-400">{formatMoney(data.tax_credits)}</span>
                </div>
                <div className="border-t border-slate-700 pt-2 mt-2">
                  <div className="flex justify-between font-semibold">
                    <span>Total Tax Liability:</span>
                    <span className="text-red-400">{formatMoney(data.total_tax_liability)}</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <Card className="border-slate-700 bg-slate-800/50">
          <CardContent className="p-4">
            <h4 className="font-semibold mb-4">Payment & Refund</h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-400">Tax Withheld:</span>
                <span className="font-medium">{formatMoney(data.tax_withheld)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Estimated Payments:</span>
                <span className="font-medium">{formatMoney(data.estimated_payments)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Refund Amount:</span>
                <span className="font-medium text-emerald-400">{formatMoney(data.refund_amount)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Amount Owed:</span>
                <span className="font-medium text-red-400">{formatMoney(data.amount_owed)}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  };

  return (
    <div className="space-y-4">
      {renderBalanceSheet()}
      {renderIncomeStatement()}
      {renderCashFlowStatement()}
      {renderTaxReturn()}
    </div>
  );
}
