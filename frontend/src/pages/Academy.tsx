import React, { useState, useEffect } from 'react';
import { GraduationCap, Award, Play, CheckCircle, HelpCircle, Loader2, ArrowLeft, Check, Sparkles } from 'lucide-react';
import { api } from '../services/api';

const Academy: React.FC = () => {
  const [courses, setCourses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Active view states
  const [selectedCourse, setSelectedCourse] = useState<any>(null);
  const [courseDetails, setCourseDetails] = useState<any>(null);
  const [detailsLoading, setDetailsLoading] = useState(false);

  // Quiz submission states
  const [quizAnswers, setQuizAnswers] = useState<number[]>([]);
  const [submittingQuiz, setSubmittingQuiz] = useState(false);
  const [quizResult, setQuizResult] = useState<any>(null);

  const fetchCourses = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.getAcademyCourses();
      if (response && response.status === 'success') {
        setCourses(response.courses);
      } else {
        setError('Failed to load courses');
      }
    } catch (e: any) {
      setError(e.message || 'Error communicating with Academy service.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCourses();
  }, []);

  const handleSelectCourse = async (course: any) => {
    setSelectedCourse(course);
    setDetailsLoading(true);
    setQuizResult(null);
    setQuizAnswers([]);
    try {
      const details = await api.getAcademyCourseDetails(course.id);
      if (details && details.status === 'success') {
        setCourseDetails(details.course);
        // Pre-fill answers with zeros
        if (details.course.quiz?.questions) {
          setQuizAnswers(new Array(details.course.quiz.questions.length).fill(-1));
        }
      }
    } catch (e: any) {
      alert(e.message || 'Failed to load course detail');
    } finally {
      setDetailsLoading(false);
    }
  };

  const handleCompleteLesson = async (lessonIdx: number) => {
    if (!selectedCourse) return;
    try {
      const result = await api.completeAcademyLesson(selectedCourse.id, lessonIdx);
      if (result && result.status === 'success') {
        // Refresh local details progress
        setCourseDetails((prev: any) => ({
          ...prev,
          progress: {
            ...prev.progress,
            completed_lessons: result.progress.completed_lessons
          }
        }));
      }
    } catch (e: any) {
      console.warn("Failed to complete lesson:", e);
    }
  };

  const handleSelectOption = (questionIdx: number, optionIdx: number) => {
    setQuizAnswers(prev => {
      const next = [...prev];
      next[questionIdx] = optionIdx;
      return next;
    });
  };

  const handleSubmitQuiz = async () => {
    if (!selectedCourse || !quizAnswers.length) return;
    if (quizAnswers.includes(-1)) {
      alert('Please answer all questions before submitting.');
      return;
    }
    
    setSubmittingQuiz(true);
    try {
      const response = await api.submitAcademyQuiz(selectedCourse.id, quizAnswers);
      if (response && response.status === 'success') {
        setQuizResult(response.result);
        if (response.result.passed) {
          // Refresh course list progress
          await fetchCourses();
        }
      }
    } catch (e: any) {
      alert(e.message || 'Quiz submission failed');
    } finally {
      setSubmittingQuiz(false);
    }
  };

  const handleBack = () => {
    setSelectedCourse(null);
    setCourseDetails(null);
    setQuizResult(null);
    fetchCourses();
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Loader2 size={40} className="text-brand-500 animate-spin mb-4" />
        <p className="text-slate-400">Loading Academy...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Catalog Grid View */}
      {!selectedCourse ? (
        <>
          {/* Header */}
          <div className="border-b border-slate-200 dark:border-slate-800 pb-4">
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white font-display flex items-center gap-2">
              <GraduationCap size={28} /> QuantAI Learning Academy
            </h1>
            <p className="text-xs text-slate-500 font-semibold mt-1">
              Boost your quant skills. Access video lessons, take quizzes, and earn digital certificates.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {courses.map((c) => {
              const isCompleted = c.progress?.completed;
              const completedCount = c.progress?.completed_lessons?.length || 0;
              const totalLessons = c.lessons_count || 0;
              const progressPercent = totalLessons > 0 ? (completedCount / totalLessons) * 100 : 0;

              return (
                <div
                  key={c.id}
                  onClick={() => handleSelectCourse(c)}
                  className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-5 shadow-sm hover:scale-[1.01] hover:shadow-md transition-all cursor-pointer flex flex-col justify-between"
                >
                  <div className="space-y-3">
                    <div className="flex justify-between items-start">
                      <span className={`px-2 py-0.5 rounded text-[9px] font-black uppercase tracking-wide ${
                        c.level === 'Advanced' ? 'bg-rose-500/10 text-rose-500' : c.level === 'Intermediate' ? 'bg-amber-500/10 text-amber-500' : 'bg-emerald-500/10 text-emerald-500'
                      }`}>{c.level}</span>
                      
                      {isCompleted && (
                        <span className="flex items-center gap-0.5 text-xs text-emerald-500 font-bold">
                          <CheckCircle size={13} /> Completed
                        </span>
                      )}
                    </div>

                    <h3 className="font-bold text-slate-900 dark:text-white tracking-wide">{c.title}</h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed mt-2 line-clamp-3 font-medium">
                      {c.description}
                    </p>
                  </div>

                  <div className="space-y-3 mt-6 pt-4 border-t border-slate-100 dark:border-slate-700/50">
                    <div className="flex justify-between items-center text-xs text-slate-500">
                      <span>Lessons: {completedCount}/{totalLessons}</span>
                      <span>{c.duration_hours} hrs</span>
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full bg-slate-100 dark:bg-slate-900 h-1.5 rounded-full overflow-hidden">
                      <div className="bg-brand-500 h-full rounded-full" style={{ width: `${progressPercent}%` }}></div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      ) : (
        // Detailed Course Shell
        <>
          <button
            onClick={handleBack}
            className="flex items-center gap-1.5 text-xs font-bold text-slate-500 hover:text-slate-800 dark:hover:text-slate-100 transition-colors uppercase tracking-wide"
          >
            <ArrowLeft size={14} /> Back to Academy
          </button>

          <div className="border-b border-slate-200 dark:border-slate-800 pb-4">
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white font-display">{selectedCourse.title}</h1>
            <p className="text-xs text-slate-500 font-semibold mt-1">{selectedCourse.description}</p>
          </div>

          {detailsLoading || !courseDetails ? (
            <div className="flex flex-col items-center justify-center min-h-[30vh]">
              <Loader2 size={30} className="text-brand-500 animate-spin mb-3" />
              <p className="text-slate-500 text-xs">Loading course modules...</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left Column: Lessons Player */}
              <div className="lg:col-span-2 space-y-6">
                <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-5 shadow-sm space-y-4">
                  <h3 className="font-bold text-sm text-slate-800 dark:text-white">Video Lessons Playlist</h3>
                  <div className="space-y-3">
                    {courseDetails.lessons?.map((les: any, idx: number) => {
                      const isLesComplete = courseDetails.progress?.completed_lessons?.includes(idx);

                      return (
                        <div
                          key={idx}
                          className="flex items-center justify-between rounded-xl p-3 border border-slate-100 dark:border-slate-700/50 bg-slate-50 dark:bg-slate-900/50"
                        >
                          <div className="flex items-center gap-3">
                            <button
                              onClick={() => handleCompleteLesson(idx)}
                              className={`p-2 rounded-lg ${
                                isLesComplete ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-200 dark:bg-slate-800 text-slate-500'
                              }`}
                            >
                              <Play size={13} fill="currentColor" />
                            </button>
                            <div>
                              <span className="text-xs font-bold text-slate-800 dark:text-white">
                                {idx + 1}. {les.title}
                              </span>
                            </div>
                          </div>

                          <button
                            onClick={() => handleCompleteLesson(idx)}
                            className={`px-3 py-1 rounded text-[10px] font-bold uppercase ${
                              isLesComplete
                                ? 'bg-emerald-500/10 text-emerald-500'
                                : 'bg-brand-500 text-white hover:bg-brand-600'
                            }`}
                          >
                            {isLesComplete ? 'Completed' : 'Mark Done'}
                          </button>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Right Column: Quiz Portal */}
              <div className="space-y-6">
                {selectedCourse.progress?.completed && selectedCourse.progress?.certificate_hash ? (
                  /* Certificate panel */
                  <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 border border-brand-500/20 rounded-2xl p-6 shadow-xl text-center relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-32 h-32 bg-brand-500/10 rounded-full blur-3xl"></div>
                    <Award className="text-brand-400 mx-auto mb-3 animate-bounce" size={48} />
                    <h3 className="text-white font-bold text-sm tracking-wide">Certification Earned!</h3>
                    <p className="text-xs text-slate-400 mt-2">You have successfully passed the curriculum verification quiz.</p>
                    <div className="bg-white/5 border border-white/5 rounded-xl p-3 mt-4 text-xs font-mono font-bold text-brand-400 uppercase select-all">
                      {selectedCourse.progress.certificate_hash}
                    </div>
                    <span className="block text-[9px] text-slate-500 mt-2 font-medium">Verify credentials secure hash</span>
                  </div>
                ) : (
                  /* Quiz panel */
                  <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-5 shadow-sm space-y-4">
                    <h3 className="font-bold text-sm text-slate-800 dark:text-white flex items-center gap-1.5">
                      <HelpCircle size={16} className="text-brand-500" /> Certification Quiz
                    </h3>
                    
                    {quizResult ? (
                      <div className="text-center space-y-3 py-6">
                        {quizResult.passed ? (
                          <>
                            <CheckCircle size={40} className="text-emerald-500 mx-auto" />
                            <h4 className="font-bold text-sm text-slate-900 dark:text-white">Passed! Score: {quizResult.score}%</h4>
                            <p className="text-xs text-slate-500 leading-relaxed">
                              Congratulations! Your certificate hash has been issued. Click back to reload.
                            </p>
                          </>
                        ) : (
                          <>
                            <XCircle size={40} className="text-rose-500 mx-auto" />
                            <h4 className="font-bold text-sm text-slate-900 dark:text-white">Failed. Score: {quizResult.score}%</h4>
                            <p className="text-xs text-slate-500 leading-relaxed">
                              You did not reach the passing score. Re-study lessons and try again.
                            </p>
                            <button
                              onClick={() => setQuizResult(null)}
                              className="px-4 py-2 bg-slate-900 text-white rounded-lg text-xs font-bold uppercase tracking-wider mt-4"
                            >
                              Retry Quiz
                            </button>
                          </>
                        )}
                      </div>
                    ) : courseDetails.quiz ? (
                      <div className="space-y-4">
                        {courseDetails.quiz.questions.map((q: any, qIdx: number) => (
                          <div key={qIdx} className="space-y-2">
                            <p className="text-xs font-bold text-slate-800 dark:text-white">{qIdx + 1}. {q.question}</p>
                            <div className="space-y-1.5">
                              {q.options.map((opt: string, optIdx: number) => {
                                const isSelected = quizAnswers[qIdx] === optIdx;

                                return (
                                  <button
                                    key={optIdx}
                                    onClick={() => handleSelectOption(qIdx, optIdx)}
                                    className={`w-full text-left p-2.5 rounded-lg text-xs font-semibold transition-all border ${
                                      isSelected
                                        ? 'bg-brand-500/10 border-brand-500 text-brand-600 dark:text-brand-400'
                                        : 'bg-slate-50 border-slate-200 dark:bg-slate-900 dark:border-slate-800 text-slate-600 dark:text-slate-400'
                                    }`}
                                  >
                                    {opt}
                                  </button>
                                );
                              })}
                            </div>
                          </div>
                        ))}

                        <button
                          disabled={submittingQuiz || quizAnswers.includes(-1)}
                          onClick={handleSubmitQuiz}
                          className="w-full py-2.5 bg-gradient-to-r from-brand-600 to-purple-600 text-white text-xs font-bold uppercase tracking-wider rounded-xl hover:from-brand-500 hover:to-purple-500 transition-all mt-4 disabled:opacity-50"
                        >
                          {submittingQuiz ? 'Grading...' : 'Submit Answers'}
                        </button>
                      </div>
                    ) : (
                      <p className="text-xs text-slate-500 italic">No quiz configured for this course.</p>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

import { XCircle } from 'lucide-react';
export default Academy;
