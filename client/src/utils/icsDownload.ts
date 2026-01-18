import { resolveApiUrl } from './apiBase';

/**
 * Utility function to download ICS file for a meeting.
 *
 * @param meetingId - The ID of the meeting to download ICS file for
 * @returns Promise that resolves when download is complete
 */
export async function downloadICSFile(meetingId: number): Promise<void> {
  try {
    const token = localStorage.getItem('creditnexus_access_token');
    const headers: HeadersInit = {
      'Authorization': `Bearer ${token}`,
    };

    const response = await fetch(resolveApiUrl(`/api/meetings/${meetingId}/ics`), {
      method: 'GET',
      headers,
    });

    if (!response.ok) {
      throw new Error(`Failed to download ICS file: ${response.statusText}`);
    }

    // Get the blob from response
    const blob = await response.blob();
    
    // Create a temporary URL for the blob
    const blobUrl = window.URL.createObjectURL(blob);
    
    // Create a temporary anchor element and trigger download
    const link = document.createElement('a');
    link.href = blobUrl;
    link.download = `meeting_${meetingId}.ics`;
    document.body.appendChild(link);
    link.click();
    
    // Clean up
    document.body.removeChild(link);
    window.URL.revokeObjectURL(blobUrl);
  } catch (error) {
    console.error('Error downloading ICS file:', error);
    throw error;
  }
}
