'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';

type CompanyOption = {
  ticker: string;
  company: string;
};

type SourceItem = {
  company: string;
  ticker: string;
  filing_type: string;
  filing_date: string;
  section: string;
  section_heading: string;
  excerpt: string;
  source_file: string;
  source_url: string;
};

type ChatResponse = {
  answer: string;
  retrieval_count: number;
  sources: SourceItem[];
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';
const DEFAULT_PROMPTS = [
  'What supply chain risks does Apple highlight?',
  'How does Nvidia discuss AI demand in recent filings?',
  "What management commentary appears in Microsoft's latest quarter?",
];

export default function Home() {
  const [companies, setCompanies] = useState<CompanyOption[]>([]);
  const [selectedCompany, setSelectedCompany] = useState('AAPL');
  const [selectedFilingType, setSelectedFilingType] = useState('10-K');
  const [question, setQuestion] = useState(DEFAULT_PROMPTS[0]);
  const [answer, setAnswer] = useState('');
  const [sources, setSources] = useState<SourceItem[]>([]);
  const [retrievalCount, setRetrievalCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    async function loadCompanies() {
      try {
        const response = await fetch(`${API_BASE_URL}/api/companies`);
        if (!response.ok) {
          throw new Error('Unable to load available companies.');
        }
        const data: CompanyOption[] = await response.json();
        setCompanies(data);
        if (data.length > 0) {
          setSelectedCompany((current) => current || data[0].ticker);
        }
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : 'Failed to load company filters.');
      }
    }

    loadCompanies();
  }, []);

  const selectedCompanyLabel = useMemo(() => {
    return companies.find((company) => company.ticker === selectedCompany)?.company ?? selectedCompany;
  }, [companies, selectedCompany]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!question.trim() || isLoading) {
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: question,
          company: selectedCompany,
          filing_type: selectedFilingType,
        }),
      });

      if (!response.ok) {
        const failure = await response.json().catch(() => ({}));
        throw new Error(failure.detail ?? 'Query failed.');
      }

      const data: ChatResponse = await response.json();
      setAnswer(data.answer);
      setSources(data.sources);
      setRetrievalCount(data.retrieval_count);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unexpected query error.');
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_#f7f2e8,_#eef2ff_45%,_#dbe4f0_100%)] text-slate-900">
      <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-8 px-4 py-8 md:px-8">
        <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-4">
            <p className="inline-flex rounded-full border border-slate-300/80 bg-white/80 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-slate-600 shadow-sm backdrop-blur">
              SEC Filing RAG Analyst
            </p>
            <div className="space-y-3">
              <h1 className="max-w-3xl text-4xl font-semibold tracking-tight text-slate-950 md:text-6xl">
                Search 10-Ks and 10-Qs with evidence, filters, and measurable retrieval behavior.
              </h1>
              <p className="max-w-2xl text-base leading-7 text-slate-600 md:text-lg">
                This workspace is designed to surface grounded answers from SEC filings while preserving the metadata
                needed for evaluation, source tracing, and retrieval experiments.
              </p>
            </div>
          </div>

          <div className="rounded-[2rem] border border-white/70 bg-white/70 p-6 shadow-[0_30px_80px_rgba(15,23,42,0.08)] backdrop-blur">
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-slate-500">Current Query Focus</p>
            <div className="mt-4 grid gap-3 text-sm text-slate-700">
              <div className="rounded-2xl bg-slate-950 px-4 py-4 text-slate-50">
                <div className="text-xs uppercase tracking-[0.2em] text-slate-300">Company</div>
                <div className="mt-1 text-lg font-semibold">{selectedCompanyLabel}</div>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Filing Type</div>
                  <div className="mt-1 text-lg font-semibold">{selectedFilingType}</div>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Retrieved Chunks</div>
                  <div className="mt-1 text-lg font-semibold">{retrievalCount}</div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
          <div className="rounded-[2rem] border border-slate-200/80 bg-white/80 p-6 shadow-[0_20px_60px_rgba(15,23,42,0.08)] backdrop-blur">
            <form className="space-y-6" onSubmit={handleSubmit}>
              <div className="grid gap-4 md:grid-cols-2">
                <label className="space-y-2">
                  <span className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Company</span>
                  <select
                    className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-slate-400"
                    value={selectedCompany}
                    onChange={(event) => setSelectedCompany(event.target.value)}
                  >
                    {companies.map((company) => (
                      <option key={company.ticker} value={company.ticker}>
                        {company.ticker} - {company.company}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="space-y-2">
                  <span className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Filing Type</span>
                  <select
                    className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-slate-400"
                    value={selectedFilingType}
                    onChange={(event) => setSelectedFilingType(event.target.value)}
                  >
                    <option value="10-K">10-K</option>
                    <option value="10-Q">10-Q</option>
                  </select>
                </label>
              </div>

              <label className="block space-y-2">
                <span className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Question</span>
                <textarea
                  className="min-h-40 w-full rounded-[1.75rem] border border-slate-200 bg-slate-50 px-5 py-4 text-sm leading-7 outline-none transition focus:border-slate-400"
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder="Ask about risk factors, management commentary, revenue trends, or product strategy."
                />
              </label>

              <div className="flex flex-wrap gap-2">
                {DEFAULT_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    className="rounded-full border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 transition hover:border-slate-400 hover:text-slate-900"
                    onClick={() => setQuestion(prompt)}
                    type="button"
                  >
                    {prompt}
                  </button>
                ))}
              </div>

              <button
                className="inline-flex items-center rounded-full bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
                disabled={isLoading}
                type="submit"
              >
                {isLoading ? 'Running SEC retrieval...' : 'Run Filing Query'}
              </button>

              {error ? (
                <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
              ) : null}
            </form>
          </div>

          <div className="grid gap-6">
            <section className="rounded-[2rem] border border-slate-200/80 bg-white/85 p-6 shadow-[0_20px_60px_rgba(15,23,42,0.08)] backdrop-blur">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Answer</p>
                  <h2 className="mt-2 text-2xl font-semibold text-slate-950">Grounded Response</h2>
                </div>
                <div className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-500">
                  {retrievalCount} evidence chunk{retrievalCount === 1 ? '' : 's'}
                </div>
              </div>
              <div className="mt-5 rounded-[1.75rem] bg-slate-50 px-5 py-5 text-sm leading-7 text-slate-700">
                {answer || 'Run a query to generate a filing-grounded answer and inspect the supporting evidence.'}
              </div>
            </section>

            <section className="rounded-[2rem] border border-slate-200/80 bg-white/85 p-6 shadow-[0_20px_60px_rgba(15,23,42,0.08)] backdrop-blur">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Evidence</p>
                  <h2 className="mt-2 text-2xl font-semibold text-slate-950">Retrieved Filing Excerpts</h2>
                </div>
              </div>

              <div className="mt-5 space-y-4">
                {sources.length === 0 ? (
                  <div className="rounded-[1.75rem] border border-dashed border-slate-200 bg-slate-50 px-5 py-6 text-sm text-slate-500">
                    Source excerpts will appear here with filing metadata once a query runs.
                  </div>
                ) : (
                  sources.map((source, index) => (
                    <article
                      key={`${source.ticker}-${source.filing_date}-${index}`}
                      className="rounded-[1.75rem] border border-slate-200 bg-slate-50 px-5 py-5"
                    >
                      <div className="flex flex-wrap gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                        <span>{source.ticker}</span>
                        <span>{source.filing_type}</span>
                        <span>{source.filing_date}</span>
                        <span>{source.section.replace('_', ' ')}</span>
                      </div>
                      <h3 className="mt-3 text-lg font-semibold text-slate-900">{source.section_heading}</h3>
                      <p className="mt-3 text-sm leading-7 text-slate-700">{source.excerpt}</p>
                      {source.source_url ? (
                        <a
                          className="mt-4 inline-flex text-sm font-medium text-slate-900 underline decoration-slate-300 underline-offset-4"
                          href={source.source_url}
                          rel="noreferrer"
                          target="_blank"
                        >
                          View SEC source
                        </a>
                      ) : null}
                    </article>
                  ))
                )}
              </div>
            </section>
          </div>
        </section>
      </main>
    </div>
  );
}
