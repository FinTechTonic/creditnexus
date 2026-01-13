import { Github, BookOpen, Rocket, Sparkles, Shield, Leaf, ArrowRight, CheckCircle, Users, Building2, FileCheck, TrendingUp } from 'lucide-react';

function App() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 via-slate-800 to-slate-900 text-slate-100">
      {/* Hero Section */}
      <section className="relative overflow-hidden py-20 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-500/10 border border-emerald-500/50 rounded-full text-emerald-400 text-sm mb-6">
              <Sparkles className="h-4 w-4" />
              <span>AI-Powered Financial Compliance Platform</span>
            </div>
            <h1 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-emerald-400 to-blue-400 bg-clip-text text-transparent">
              CreditNexus
            </h1>
            <p className="text-xl md:text-2xl text-slate-300 mb-8 max-w-3xl mx-auto">
              Streamline Credit Verification & Compliance for Financial Institutions
            </p>
            <p className="text-lg text-slate-400 mb-12 max-w-2xl mx-auto">
              Automate credit agreement processing, verify bonds and loans, and ensure regulatory compliance
              with AI-powered document extraction and satellite-based ground truth verification.
            </p>
            <div className="flex flex-wrap items-center justify-center gap-4">
              <a
                href="https://github.com/yourusername/creditnexus"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center px-6 py-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition-colors"
              >
                <Github className="h-5 w-5 mr-2" />
                View on GitHub
              </a>
              <a
                href="https://docs.creditnexus.com"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center px-6 py-3 border border-slate-600 text-slate-300 hover:bg-slate-800 rounded-lg transition-colors"
              >
                <BookOpen className="h-5 w-5 mr-2" />
                Documentation
              </a>
              <a
                href="/apply"
                className="inline-flex items-center px-6 py-3 border border-slate-600 text-slate-300 hover:bg-slate-800 rounded-lg transition-colors"
              >
                <Rocket className="h-5 w-5 mr-2" />
                Get Started
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Value Proposition Section */}
      <section className="py-20 px-4 bg-slate-800/50">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold mb-4">Built for Financial Institutions</h2>
            <p className="text-xl text-slate-400 max-w-2xl mx-auto">
              Streamline operations, reduce risk, and ensure compliance
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div className="p-6 bg-slate-800/50 border border-slate-700 rounded-lg hover:border-emerald-500/50 transition-colors">
              <div className="w-12 h-12 bg-emerald-500/10 rounded-lg flex items-center justify-center mb-4">
                <Building2 className="h-6 w-6 text-emerald-400" />
              </div>
              <h3 className="text-xl font-semibold mb-2">Loan Granting Companies</h3>
              <p className="text-slate-400">
                Automate credit agreement processing, extract structured data, and verify loan terms
                with AI-powered document analysis. Reduce processing time from days to minutes.
              </p>
            </div>

            <div className="p-6 bg-slate-800/50 border border-slate-700 rounded-lg hover:border-emerald-500/50 transition-colors">
              <div className="w-12 h-12 bg-blue-500/10 rounded-lg flex items-center justify-center mb-4">
                <FileCheck className="h-6 w-6 text-blue-400" />
              </div>
              <h3 className="text-xl font-semibold mb-2">Company Bond Verification</h3>
              <p className="text-slate-400">
                Verify corporate bonds and debt instruments with automated compliance checking.
                Ensure all bond terms meet regulatory requirements and internal policies.
              </p>
            </div>

            <div className="p-6 bg-slate-800/50 border border-slate-700 rounded-lg hover:border-emerald-500/50 transition-colors">
              <div className="w-12 h-12 bg-green-500/10 rounded-lg flex items-center justify-center mb-4">
                <Users className="h-6 w-6 text-green-400" />
              </div>
              <h3 className="text-xl font-semibold mb-2">Individual Bond Verification</h3>
              <p className="text-slate-400">
                Process and verify individual bond applications with automated risk assessment
                and compliance validation. Accelerate approval workflows.
              </p>
            </div>

            <div className="p-6 bg-slate-800/50 border border-slate-700 rounded-lg hover:border-emerald-500/50 transition-colors">
              <div className="w-12 h-12 bg-yellow-500/10 rounded-lg flex items-center justify-center mb-4">
                <Shield className="h-6 w-6 text-yellow-400" />
              </div>
              <h3 className="text-xl font-semibold mb-2">Regulatory Compliance</h3>
              <p className="text-slate-400">
                Real-time policy enforcement for MiCA, Basel III, and FATF regulations.
                Policy-as-code ensures consistent compliance across all transactions.
              </p>
            </div>

            <div className="p-6 bg-slate-800/50 border border-slate-700 rounded-lg hover:border-emerald-500/50 transition-colors">
              <div className="w-12 h-12 bg-purple-500/10 rounded-lg flex items-center justify-center mb-4">
                <Leaf className="h-6 w-6 text-purple-400" />
              </div>
              <h3 className="text-xl font-semibold mb-2">Satellite Verification</h3>
              <p className="text-slate-400">
                Verify sustainability-linked loans using satellite imagery and NDVI analysis.
                Ground truth verification for ESG compliance.
              </p>
            </div>

            <div className="p-6 bg-slate-800/50 border border-slate-700 rounded-lg hover:border-emerald-500/50 transition-colors">
              <div className="w-12 h-12 bg-cyan-500/10 rounded-lg flex items-center justify-center mb-4">
                <TrendingUp className="h-6 w-6 text-cyan-400" />
              </div>
              <h3 className="text-xl font-semibold mb-2">Access to Finance</h3>
              <p className="text-slate-400">
                Streamline application processes for individuals and businesses seeking credit.
                AI-powered assessment accelerates decision-making.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* About Section */}
      <section className="py-20 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold mb-4">About CreditNexus</h2>
            <p className="text-xl text-slate-400 max-w-2xl mx-auto">
              A startup focused on democratizing access to finance and ensuring compliance
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <h3 className="text-2xl font-semibold mb-4">Our Mission</h3>
              <p className="text-slate-300 mb-4">
                CreditNexus was founded by a team with over 20 years of combined experience in the financial industry.
                Our deep understanding of banking operations, payment systems, and regulatory compliance drives our
                mission to bridge the gap between complex financial regulations and accessible credit services.
                We believe that compliance shouldn't be a barrier to financial inclusion.
              </p>
              <p className="text-slate-300 mb-4">
                Our platform automates the tedious process of credit agreement verification, making it
                faster and more reliable for financial institutions to process loans while ensuring
                full regulatory compliance.
              </p>
              <p className="text-slate-300">
                By combining AI-powered document extraction with satellite-based verification, we help
                financial institutions reduce operational costs, minimize risk, and accelerate time-to-market
                for new credit products.
              </p>
            </div>
            <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-8">
              <h3 className="text-xl font-semibold mb-6">Key Focus Areas</h3>
              <ul className="space-y-4">
                <li className="flex items-start gap-3">
                  <CheckCircle className="h-6 w-6 text-emerald-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-semibold mb-1">Compliance Automation</h4>
                    <p className="text-slate-400 text-sm">
                      Automated policy enforcement ensures every transaction meets regulatory requirements
                    </p>
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <CheckCircle className="h-6 w-6 text-emerald-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-semibold mb-1">Access to Finance</h4>
                    <p className="text-slate-400 text-sm">
                      Streamlined application processes for individuals and businesses seeking credit
                    </p>
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <CheckCircle className="h-6 w-6 text-emerald-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-semibold mb-1">Verification & Risk Assessment</h4>
                    <p className="text-slate-400 text-sm">
                      AI and satellite-based verification for bonds, loans, and sustainability claims
                    </p>
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <CheckCircle className="h-6 w-6 text-emerald-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-semibold mb-1">CDM Standardization</h4>
                    <p className="text-slate-400 text-sm">
                      Full FINOS CDM compliance ensures interoperability with existing financial systems
                    </p>
                  </div>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Team Section */}
      <section className="py-20 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold mb-4">Our Team</h2>
            <p className="text-xl text-slate-400 max-w-2xl mx-auto">
              Experienced professionals with deep financial industry expertise
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="p-6 bg-slate-800/50 border border-slate-700 rounded-lg text-center">
              <div className="w-24 h-24 bg-gradient-to-br from-emerald-500 to-blue-600 rounded-full mx-auto mb-4 flex items-center justify-center">
                <Users className="h-12 w-12 text-white" />
              </div>
              <h3 className="text-xl font-semibold mb-2">Joseph Pollack</h3>
              <p className="text-emerald-400 mb-2">Chief Information Officer</p>
              <p className="text-sm text-slate-400">Strategic technology leadership and architecture</p>
            </div>

            <div className="p-6 bg-slate-800/50 border border-slate-700 rounded-lg text-center">
              <div className="w-24 h-24 bg-gradient-to-br from-emerald-500 to-blue-600 rounded-full mx-auto mb-4 flex items-center justify-center">
                <Users className="h-12 w-12 text-white" />
              </div>
              <h3 className="text-xl font-semibold mb-2">Biniyam Ajew</h3>
              <p className="text-emerald-400 mb-2">Senior Developer</p>
              <p className="text-sm text-slate-400">Full-stack development and system architecture</p>
            </div>

            <div className="p-6 bg-slate-800/50 border border-slate-700 rounded-lg text-center">
              <div className="w-24 h-24 bg-gradient-to-br from-emerald-500 to-blue-600 rounded-full mx-auto mb-4 flex items-center justify-center">
                <Users className="h-12 w-12 text-white" />
              </div>
              <h3 className="text-xl font-semibold mb-2">Boris Li</h3>
              <p className="text-emerald-400 mb-2">Junior Developer</p>
              <p className="text-sm text-slate-400">
                10 years of experience at Citibank and Mastercard in payment systems, 
                banking operations, and financial technology
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Technology Stack Section */}
      <section className="py-20 px-4 bg-slate-800/50">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold mb-4">Technology Stack</h2>
            <p className="text-xl text-slate-400 max-w-2xl mx-auto">
              Built with modern, production-ready technologies
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="p-6 bg-slate-800/50 border border-slate-700 rounded-lg text-center">
              <h3 className="text-lg font-semibold mb-2">Backend</h3>
              <ul className="text-sm text-slate-400 space-y-1">
                <li>FastAPI</li>
                <li>SQLAlchemy 2.0</li>
                <li>PostgreSQL</li>
                <li>Pydantic 2.0</li>
              </ul>
            </div>

            <div className="p-6 bg-slate-800/50 border border-slate-700 rounded-lg text-center">
              <h3 className="text-lg font-semibold mb-2">Frontend</h3>
              <ul className="text-sm text-slate-400 space-y-1">
                <li>React 18</li>
                <li>TypeScript</li>
                <li>Vite</li>
                <li>Tailwind CSS</li>
              </ul>
            </div>

            <div className="p-6 bg-slate-800/50 border border-slate-700 rounded-lg text-center">
              <h3 className="text-lg font-semibold mb-2">AI/ML</h3>
              <ul className="text-sm text-slate-400 space-y-1">
                <li>OpenAI GPT-4o</li>
                <li>LangChain</li>
                <li>TorchGeo</li>
                <li>vLLM / HuggingFace</li>
              </ul>
            </div>

            <div className="p-6 bg-slate-800/50 border border-slate-700 rounded-lg text-center">
              <h3 className="text-lg font-semibold mb-2">Standards</h3>
              <ul className="text-sm text-slate-400 space-y-1">
                <li>FINOS CDM</li>
                <li>FDC3 2.0</li>
                <li>ISO 8601</li>
                <li>x402 Protocol</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* GitHub Integration Section */}
      <section className="py-20 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="p-12 bg-slate-800 border border-slate-700 rounded-lg">
            <div className="flex flex-col md:flex-row items-center justify-between gap-8">
              <div className="flex-1">
                <h2 className="text-3xl font-bold mb-4">Open Source & Community Driven</h2>
                <p className="text-lg text-slate-400 mb-6">
                  CreditNexus is open source and welcomes contributions from the community.
                  Star us on GitHub to stay updated with the latest features and improvements.
                </p>
                <div className="flex flex-wrap gap-4">
                  <a
                    href="https://github.com/yourusername/creditnexus"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
                  >
                    <Github className="h-5 w-5 mr-2" />
                    View Repository
                  </a>
                  <a
                    href="https://docs.creditnexus.com"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center px-6 py-3 border border-slate-600 text-slate-300 hover:bg-slate-800 rounded-lg transition-colors"
                  >
                    <BookOpen className="h-5 w-5 mr-2" />
                    Read Documentation
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </a>
                </div>
              </div>
              <div className="flex-shrink-0">
                <div className="w-32 h-32 bg-gradient-to-br from-emerald-500 to-blue-600 rounded-2xl flex items-center justify-center">
                  <Github className="h-16 w-16 text-white" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-4xl font-bold mb-6">Ready to Get Started?</h2>
          <p className="text-xl text-slate-400 mb-8">
            Join the future of financial operations with CreditNexus
          </p>
          <div className="flex flex-wrap items-center justify-center gap-4">
            <a
              href="/apply"
              className="inline-flex items-center px-6 py-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition-colors"
            >
              <Rocket className="h-5 w-5 mr-2" />
              Start Application
            </a>
            <a
              href="https://docs.creditnexus.com"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center px-6 py-3 border border-slate-600 text-slate-300 hover:bg-slate-800 rounded-lg transition-colors"
            >
              <BookOpen className="h-5 w-5 mr-2" />
              View Documentation
            </a>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-700 py-12 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="text-slate-400">
              <p>&copy; 2024 CreditNexus. Open source under MIT License.</p>
            </div>
            <div className="flex items-center gap-6">
              <a
                href="https://github.com/yourusername/creditnexus"
                target="_blank"
                rel="noopener noreferrer"
                className="text-slate-400 hover:text-slate-100 transition-colors"
              >
                <Github className="h-5 w-5" />
              </a>
              <a
                href="https://docs.creditnexus.com"
                target="_blank"
                rel="noopener noreferrer"
                className="text-slate-400 hover:text-slate-100 transition-colors"
              >
                <BookOpen className="h-5 w-5" />
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
