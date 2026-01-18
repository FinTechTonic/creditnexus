/**
 * Borrower Contact Manager Component
 * 
 * Manages borrower contact information for loan recovery communications.
 */

import { useState, useEffect, useCallback } from 'react';
import { fetchWithAuth } from '@/context/AuthContext';
import { Card, CardContent } from '@/components/ui/card'; // CardHeader, CardTitle removed - unused
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import {
  User,
  Phone,
  Mail,
  Plus,
  Edit,
  Trash2,
  Loader2,
  // CheckCircle, XCircle, AlertCircle removed - unused
} from 'lucide-react';
import type {
  BorrowerContact,
  BorrowerContactCreate,
  BorrowerContactUpdate,
  PreferredContactMethod
} from '@/types/recovery';

interface BorrowerContactManagerProps {
  dealId: number;
  onContactUpdate?: () => void;
}

export function BorrowerContactManager({ dealId, onContactUpdate }: BorrowerContactManagerProps) {
  const [contacts, setContacts] = useState<BorrowerContact[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingContact, setEditingContact] = useState<BorrowerContact | null>(null);
  
  // Form state
  const [formData, setFormData] = useState<BorrowerContactCreate>({
    deal_id: dealId,
    contact_name: '',
    phone_number: '',
    email: '',
    preferred_contact_method: 'sms',
    is_primary: false,
    is_active: true
  });

  // Fetch contacts
  const fetchContacts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchWithAuth(`/api/recovery/contacts?deal_id=${dealId}`);
      if (!response.ok) throw new Error('Failed to fetch contacts');
      
      const data = await response.json();
      setContacts(data.contacts || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load contacts');
      console.error('Error fetching contacts:', err);
    } finally {
      setLoading(false);
    }
  }, [dealId]);

  useEffect(() => {
    fetchContacts();
  }, [fetchContacts]);

  // Validate phone number (E.164 format)
  const validatePhoneNumber = (phone: string): boolean => {
    if (!phone) return true; // Optional field
    // E.164 format: +[country code][number] (max 15 digits total)
    const e164Regex = /^\+[1-9]\d{1,14}$/;
    return e164Regex.test(phone);
  };

  // Validate email
  const validateEmail = (email: string): boolean => {
    if (!email) return true; // Optional field
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  // Handle create contact
  const handleCreateContact = async () => {
    // Validation
    if (!formData.contact_name.trim()) {
      setError('Contact name is required');
      return;
    }
    
    if (formData.phone_number && !validatePhoneNumber(formData.phone_number)) {
      setError('Phone number must be in E.164 format (e.g., +1234567890)');
      return;
    }
    
    if (formData.email && !validateEmail(formData.email)) {
      setError('Invalid email address');
      return;
    }

    setLoading(true);
    setError(null);
    
    try {
      const response = await fetchWithAuth('/api/recovery/contacts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create contact');
      }
      
      await fetchContacts();
      setShowCreateModal(false);
      resetForm();
      onContactUpdate?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create contact');
      console.error('Error creating contact:', err);
    } finally {
      setLoading(false);
    }
  };

  // Handle update contact
  const handleUpdateContact = async (contactId: number, updates: BorrowerContactUpdate) => {
    setLoading(true);
    setError(null);
    
    // Validation
    if (updates.phone_number && !validatePhoneNumber(updates.phone_number)) {
      setError('Phone number must be in E.164 format (e.g., +1234567890)');
      setLoading(false);
      return;
    }
    
    if (updates.email && !validateEmail(updates.email)) {
      setError('Invalid email address');
      setLoading(false);
      return;
    }
    
    try {
      const response = await fetchWithAuth(`/api/recovery/contacts/${contactId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to update contact');
      }
      
      await fetchContacts();
      setEditingContact(null);
      onContactUpdate?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update contact');
      console.error('Error updating contact:', err);
    } finally {
      setLoading(false);
    }
  };

  // Handle delete contact (deactivate)
  const handleDeleteContact = async (contactId: number) => {
    if (!confirm('Are you sure you want to deactivate this contact?')) {
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      await handleUpdateContact(contactId, { is_active: false });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to deactivate contact');
    } finally {
      setLoading(false);
    }
  };

  // Reset form
  const resetForm = () => {
    setFormData({
      deal_id: dealId,
      contact_name: '',
      phone_number: '',
      email: '',
      preferred_contact_method: 'sms',
      is_primary: false,
      is_active: true
    });
    setError(null);
  };

  // Open edit modal
  const openEditModal = (contact: BorrowerContact) => {
    setEditingContact(contact);
    setFormData({
      deal_id: dealId,
      contact_name: contact.contact_name,
      phone_number: contact.phone_number || '',
      email: contact.email || '',
      preferred_contact_method: contact.preferred_contact_method,
      is_primary: contact.is_primary,
      is_active: contact.is_active
    });
  };

  // Close modals
  const closeModals = () => {
    setShowCreateModal(false);
    setEditingContact(null);
    resetForm();
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-slate-100">Borrower Contacts</h3>
        <Button
          size="sm"
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Add Contact
        </Button>
      </div>

      {error && (
        <div className="p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {loading && contacts.length === 0 ? (
        <div className="text-center py-8 text-slate-400">
          <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
          <p>Loading contacts...</p>
        </div>
      ) : contacts.length === 0 ? (
        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="p-6 text-center text-slate-400">
            <User className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>No contacts found. Add a contact to enable recovery communications.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {contacts.map((contact) => (
            <Card
              key={contact.id}
              className={`bg-slate-800 border-slate-700 ${
                !contact.is_active ? 'opacity-50' : ''
              }`}
            >
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h4 className="font-semibold text-slate-100">{contact.contact_name}</h4>
                      {contact.is_primary && (
                        <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/50 text-xs">
                          Primary
                        </Badge>
                      )}
                      {!contact.is_active && (
                        <Badge className="bg-gray-500/20 text-gray-400 border-gray-500/50 text-xs">
                          Inactive
                        </Badge>
                      )}
                    </div>
                    <div className="space-y-1 text-sm text-slate-400">
                      {contact.phone_number && (
                        <div className="flex items-center gap-2">
                          <Phone className="w-4 h-4" />
                          <span>{contact.phone_number}</span>
                        </div>
                      )}
                      {contact.email && (
                        <div className="flex items-center gap-2">
                          <Mail className="w-4 h-4" />
                          <span>{contact.email}</span>
                        </div>
                      )}
                      <div className="flex items-center gap-2">
                        <span className="capitalize">Preferred: {contact.preferred_contact_method}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => openEditModal(contact)}
                      className="text-blue-400 hover:text-blue-300"
                    >
                      <Edit className="w-4 h-4" />
                    </Button>
                    {contact.is_active && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDeleteContact(contact.id)}
                        className="text-red-400 hover:text-red-300"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      <Dialog open={showCreateModal || editingContact !== null} onOpenChange={closeModals}>
        <DialogContent className="bg-slate-800 border-slate-700 text-slate-100 max-w-md">
          <DialogHeader>
            <DialogTitle>
              {editingContact ? 'Edit Contact' : 'Add New Contact'}
            </DialogTitle>
            <DialogDescription className="text-slate-400">
              {editingContact
                ? 'Update borrower contact information'
                : 'Add a new borrower contact for recovery communications'}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 mt-4">
            <div>
              <Label htmlFor="contact_name" className="text-slate-300">
                Contact Name *
              </Label>
              <Input
                id="contact_name"
                value={formData.contact_name || ''}
                onChange={(e) => setFormData({ ...formData, contact_name: e.target.value })}
                className="bg-slate-900 border-slate-700 text-slate-100"
                placeholder="John Doe"
              />
            </div>

            <div>
              <Label htmlFor="phone_number" className="text-slate-300">
                Phone Number (E.164 format)
              </Label>
              <Input
                id="phone_number"
                value={formData.phone_number || ''}
                onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
                className="bg-slate-900 border-slate-700 text-slate-100"
                placeholder="+1234567890"
              />
              <p className="text-xs text-slate-500 mt-1">
                Format: +[country code][number] (e.g., +1234567890)
              </p>
            </div>

            <div>
              <Label htmlFor="email" className="text-slate-300">
                Email Address
              </Label>
              <Input
                id="email"
                type="email"
                value={formData.email || ''}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="bg-slate-900 border-slate-700 text-slate-100"
                placeholder="john.doe@example.com"
              />
            </div>

            <div>
              <Label htmlFor="preferred_contact_method" className="text-slate-300">
                Preferred Contact Method
              </Label>
              <select
                id="preferred_contact_method"
                value={formData.preferred_contact_method || 'sms'}
                onChange={(e) => setFormData({ ...formData, preferred_contact_method: e.target.value as PreferredContactMethod })}
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-slate-100"
              >
                <option value="sms">SMS</option>
                <option value="voice">Voice Call</option>
                <option value="email">Email</option>
              </select>
            </div>

            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.is_primary}
                  onChange={(e) => setFormData({ ...formData, is_primary: e.target.checked })}
                  className="w-4 h-4 rounded border-slate-700 bg-slate-900"
                />
                <span className="text-sm text-slate-300">Primary Contact</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="w-4 h-4 rounded border-slate-700 bg-slate-900"
                />
                <span className="text-sm text-slate-300">Active</span>
              </label>
            </div>

            {error && (
              <div className="p-2 bg-red-500/20 border border-red-500/50 rounded text-red-400 text-sm">
                {error}
              </div>
            )}

            <div className="flex justify-end gap-2 pt-4">
              <Button
                variant="outline"
                onClick={closeModals}
                disabled={loading}
                className="border-slate-700 text-slate-300 hover:bg-slate-700"
              >
                Cancel
              </Button>
              <Button
                onClick={editingContact ? () => handleUpdateContact(editingContact.id, formData) : handleCreateContact}
                disabled={loading}
                className="bg-emerald-600 hover:bg-emerald-700"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                    {editingContact ? 'Updating...' : 'Creating...'}
                  </>
                ) : (
                  editingContact ? 'Update' : 'Create'
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
