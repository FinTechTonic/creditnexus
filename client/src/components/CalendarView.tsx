import { useState, useEffect, useCallback } from 'react';
import { Calendar, momentLocalizer } from 'react-big-calendar';
import type { View, Event } from 'react-big-calendar';
import moment from 'moment';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
  Plus,
  AlertCircle
} from 'lucide-react';
import { fetchWithAuth } from '@/context/AuthContext';
import { downloadICSFile } from '@/utils/icsDownload';
import { MeetingModal } from './MeetingModal';
import { Skeleton } from '@/components/ui/skeleton';

const localizer = momentLocalizer(moment);

interface Meeting {
  id: number;
  title: string;
  description: string | null;
  scheduled_at: string;
  duration_minutes: number;
  meeting_type: string;
  application_id: number | null;
  organizer_id: number | null;
  attendees: Array<{
    name: string;
    email: string;
  }> | null;
  meeting_link: string | null;
  ics_file_path: string | null;
  created_at: string;
  updated_at: string;
}

interface CalendarEvent extends Event {
  meetingId?: number;
  meeting?: Meeting;
}

export function CalendarView() {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentView, setCurrentView] = useState<View>('month');
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);

  useEffect(() => {
    fetchMeetings();
  }, []);

  const fetchMeetings = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetchWithAuth('/api/meetings');
      
      if (!response.ok) {
        throw new Error('Failed to fetch meetings');
      }

      const data = await response.json();
      
      // Handle both array and object response formats
      const meetings: Meeting[] = Array.isArray(data) ? data : (data.meetings || []);
      
      // Convert meetings to calendar events
      const calendarEvents: CalendarEvent[] = meetings.map(meeting => {
        const start = new Date(meeting.scheduled_at);
        const end = new Date(start.getTime() + meeting.duration_minutes * 60000);
        
        return {
          id: meeting.id,
          title: meeting.title,
          start,
          end,
          meetingId: meeting.id,
          meeting,
        };
      });

      setEvents(calendarEvents);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load meetings');
      console.error('Error fetching meetings:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectSlot = useCallback(({ start }: { start: Date }) => {
    setSelectedDate(start);
    setShowModal(true);
  }, []);

  const handleSelectEvent = useCallback((event: CalendarEvent) => {
    setSelectedEvent(event);
    setShowModal(true);
  }, []);

  const handleDownloadICS = async (meetingId: number) => {
    try {
      await downloadICSFile(meetingId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to download ICS file');
    }
  };

  const handleModalClose = () => {
    setShowModal(false);
    setSelectedEvent(null);
    setSelectedDate(null);
    fetchMeetings(); // Refresh meetings after modal closes
  };

  const eventStyleGetter = (event: CalendarEvent) => {
    const meetingType = event.meeting?.meeting_type || 'default';
    let backgroundColor = '#3b82f6'; // Default blue
    
    switch (meetingType) {
      case 'application_review':
        backgroundColor = '#10b981'; // Emerald
        break;
      case 'consultation':
        backgroundColor = '#8b5cf6'; // Purple
        break;
      case 'follow_up':
        backgroundColor = '#f59e0b'; // Amber
        break;
      default:
        backgroundColor = '#3b82f6'; // Blue
    }

    return {
      style: {
        backgroundColor,
        borderRadius: '4px',
        opacity: 0.8,
        color: 'white',
        border: '0px',
        display: 'block',
      },
    };
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100">Calendar</h1>
          <p className="text-slate-400 mt-1">View and manage your meetings</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            onClick={() => {
              setSelectedDate(new Date());
              setShowModal(true);
            }}
            className="bg-emerald-600 hover:bg-emerald-500 text-white"
          >
            <Plus className="h-4 w-4 mr-2" />
            New Meeting
          </Button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4 flex items-center gap-2 text-red-400">
          <AlertCircle className="h-5 w-5" />
          <span>{error}</span>
        </div>
      )}

      {/* Calendar */}
      <Card className="bg-slate-800 border-slate-700">
        <CardContent className="p-6">
          <div style={{ height: '600px' }}>
            <Calendar
              localizer={localizer}
              events={events}
              startAccessor="start"
              endAccessor="end"
              view={currentView}
              onView={setCurrentView}
              date={currentDate}
              onNavigate={setCurrentDate}
              onSelectSlot={handleSelectSlot}
              onSelectEvent={handleSelectEvent}
              selectable
              eventPropGetter={eventStyleGetter}
              style={{
                height: '100%',
                color: '#e2e8f0',
              }}
              className="calendar-dark"
            />
          </div>
        </CardContent>
      </Card>

      {/* Meeting Details Modal */}
      {showModal && (
        <MeetingModal
          isOpen={showModal}
          onClose={handleModalClose}
          meeting={selectedEvent?.meeting || null}
          selectedDate={selectedDate}
          onDownloadICS={handleDownloadICS}
        />
      )}

      <style>{`
        .calendar-dark {
          background-color: #1e293b;
          color: #e2e8f0;
        }
        .calendar-dark .rbc-header {
          background-color: #0f172a;
          color: #cbd5e1;
          border-bottom: 1px solid #334155;
          padding: 10px 0;
        }
        .calendar-dark .rbc-day-bg {
          background-color: #1e293b;
        }
        .calendar-dark .rbc-off-range-bg {
          background-color: #0f172a;
        }
        .calendar-dark .rbc-today {
          background-color: #1e293b;
        }
        .calendar-dark .rbc-toolbar {
          background-color: #0f172a;
          color: #cbd5e1;
          padding: 10px;
          border-bottom: 1px solid #334155;
        }
        .calendar-dark .rbc-toolbar button {
          color: #cbd5e1;
          background-color: #1e293b;
          border: 1px solid #334155;
        }
        .calendar-dark .rbc-toolbar button:hover {
          background-color: #334155;
        }
        .calendar-dark .rbc-toolbar button.rbc-active {
          background-color: #10b981;
          color: white;
        }
        .calendar-dark .rbc-time-slot {
          border-top: 1px solid #334155;
        }
        .calendar-dark .rbc-time-header-content {
          border-left: 1px solid #334155;
        }
        .calendar-dark .rbc-time-content {
          border-top: 1px solid #334155;
        }
        .calendar-dark .rbc-day-slot .rbc-time-slot {
          border-top: 1px solid #334155;
        }
        .calendar-dark .rbc-event {
          padding: 2px 5px;
          border-radius: 4px;
        }
        .calendar-dark .rbc-selected {
          background-color: #10b981 !important;
        }
      `}</style>
    </div>
  );
}
