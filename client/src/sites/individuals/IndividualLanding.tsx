import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { 
  ArrowRight,
  Shield,
  DollarSign,
  User,
  Zap
} from 'lucide-react';

export function IndividualLanding() {
  return (
    <div className="min-h-screen bg-[var(--color-background)] text-[var(--color-foreground)]">
      {/* Hero Section */}
      <section className="relative overflow-hidden py-20 px-4 bg-[var(--color-hero-bg)]">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h1 className="text-5xl md:text-6xl font-bold mb-6 bg-[var(--color-gradient-text)] bg-clip-text text-transparent">
              Apply for Credit with CreditNexus
            </h1>
            <p className="text-xl md:text-2xl text-[var(--color-muted-foreground)] mb-8 max-w-3xl mx-auto">
              Fast, transparent, AI-powered loan processing
            </p>
            <p className="text-lg text-[var(--color-muted-foreground)] mb-12 max-w-2xl mx-auto">
              Get the credit you need with a streamlined application process powered by advanced AI technology.
              Our platform ensures fast approval, competitive rates, and complete transparency.
            </p>
            <Button asChild size="lg" className="gap-2">
              <Link to="/apply/individual">
                Start Application
                <ArrowRight className="h-5 w-5" />
              </Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section className="py-20 px-4 bg-[var(--color-background)]">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold mb-4">Why Choose CreditNexus?</h2>
            <p className="text-xl text-[var(--color-muted-foreground)] max-w-2xl mx-auto">
              Experience the future of credit applications
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <Card className="bg-[var(--color-card-bg)]">
              <CardContent className="p-6 text-center">
                <div className="w-12 h-12 bg-[var(--color-icon-bg-emerald)] rounded-lg flex items-center justify-center mx-auto mb-4">
                  <Zap className="h-6 w-6 text-[var(--color-icon-emerald)]" />
                </div>
                <h3 className="text-xl font-semibold mb-2">Fast Approval</h3>
                <p className="text-[var(--color-muted-foreground)] text-sm">
                  Get decisions in minutes, not days
                </p>
              </CardContent>
            </Card>

            <Card className="bg-[var(--color-card-bg)]">
              <CardContent className="p-6 text-center">
                <div className="w-12 h-12 bg-[var(--color-icon-bg-blue)] rounded-lg flex items-center justify-center mx-auto mb-4">
                  <Shield className="h-6 w-6 text-[var(--color-icon-blue)]" />
                </div>
                <h3 className="text-xl font-semibold mb-2">Transparent Process</h3>
                <p className="text-[var(--color-muted-foreground)] text-sm">
                  Complete visibility into your application status
                </p>
              </CardContent>
            </Card>

            <Card className="bg-[var(--color-card-bg)]">
              <CardContent className="p-6 text-center">
                <div className="w-12 h-12 bg-[var(--color-icon-bg-yellow)] rounded-lg flex items-center justify-center mx-auto mb-4">
                  <DollarSign className="h-6 w-6 text-[var(--color-icon-yellow)]" />
                </div>
                <h3 className="text-xl font-semibold mb-2">Competitive Rates</h3>
                <p className="text-[var(--color-muted-foreground)] text-sm">
                  Best rates tailored to your profile
                </p>
              </CardContent>
            </Card>

            <Card className="bg-[var(--color-card-bg)]">
              <CardContent className="p-6 text-center">
                <div className="w-12 h-12 bg-[var(--color-icon-bg-purple)] rounded-lg flex items-center justify-center mx-auto mb-4">
                  <User className="h-6 w-6 text-[var(--color-icon-purple)]" />
                </div>
                <h3 className="text-xl font-semibold mb-2">Digital-First</h3>
                <p className="text-[var(--color-muted-foreground)] text-sm">
                  Complete your application entirely online
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section className="py-20 px-4 bg-[var(--color-background)]">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold mb-4">How It Works</h2>
            <p className="text-xl text-[var(--color-muted-foreground)] max-w-2xl mx-auto">
              Simple steps to get the credit you need
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-16 h-16 bg-[var(--color-step-bg)] rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl font-bold text-[var(--color-step-text)]">1</span>
              </div>
              <h3 className="text-xl font-semibold mb-2">Apply Online</h3>
              <p className="text-[var(--color-muted-foreground)]">
                Fill out our simple application form with your personal and financial information
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-[var(--color-step-bg)] rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl font-bold text-[var(--color-step-text)]">2</span>
              </div>
              <h3 className="text-xl font-semibold mb-2">AI Review</h3>
              <p className="text-[var(--color-muted-foreground)]">
                Our AI-powered system reviews your application and verifies information instantly
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-[var(--color-step-bg)] rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl font-bold text-[var(--color-step-text)]">3</span>
              </div>
              <h3 className="text-xl font-semibold mb-2">Get Approved</h3>
              <p className="text-[var(--color-muted-foreground)]">
                Receive your decision quickly and access funds once approved
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="py-20 px-4 bg-[var(--color-background)]">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold mb-4">Frequently Asked Questions</h2>
          </div>

          <div className="space-y-6">
            <Card className="bg-[var(--color-card-bg)]">
              <CardContent className="p-6">
                <h3 className="text-lg font-semibold mb-2">How long does the application process take?</h3>
                <p className="text-[var(--color-muted-foreground)]">
                  Most applications are reviewed within minutes. You'll receive a decision typically within 24-48 hours.
                </p>
              </CardContent>
            </Card>

            <Card className="bg-[var(--color-card-bg)]">
              <CardContent className="p-6">
                <h3 className="text-lg font-semibold mb-2">What documents do I need?</h3>
                <p className="text-[var(--color-muted-foreground)]">
                  You'll need a valid ID, proof of income, and bank statements. All documents can be uploaded securely through our platform.
                </p>
              </CardContent>
            </Card>

            <Card className="bg-[var(--color-card-bg)]">
              <CardContent className="p-6">
                <h3 className="text-lg font-semibold mb-2">Is my information secure?</h3>
                <p className="text-[var(--color-muted-foreground)]">
                  Yes, we use bank-level encryption and follow strict security protocols to protect your personal and financial information.
                </p>
              </CardContent>
            </Card>

            <Card className="bg-[var(--color-card-bg)]">
              <CardContent className="p-6">
                <h3 className="text-lg font-semibold mb-2">What credit score do I need?</h3>
                <p className="text-[var(--color-muted-foreground)]">
                  We consider applications from a wide range of credit profiles. Our AI-powered system evaluates multiple factors beyond just credit score.
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4 bg-[var(--color-cta-bg)]">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-4xl font-bold mb-6">Ready to Apply?</h2>
          <p className="text-xl text-[var(--color-muted-foreground)] mb-8">
            Start your application today and get the credit you need
          </p>
          <Button asChild size="lg" className="gap-2">
            <Link to="/apply/individual">
              Start Application
              <ArrowRight className="h-5 w-5" />
            </Link>
          </Button>
        </div>
      </section>
    </div>
  );
}
