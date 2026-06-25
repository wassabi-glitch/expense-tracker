import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { useTaxonomyQuery } from "./hooks/useTaxonomyQuery";
import { useTaxonomyMutations } from "./hooks/useTaxonomyMutations";
import { formatUzs } from "../../lib/format";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Skeleton } from "../../components/ui/skeleton";
import { Input } from "../../components/ui/input";
import { Button } from "../../components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../../components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../../components/ui/dialog";
import { MoreHorizontal, Pencil, Archive, ArchiveRestore, Trash2, Combine, Plus } from "lucide-react";
import { CATEGORIES } from "../../lib/category";

function TaxonomyTagCard({ tag, categoryTags, updateMutation, deleteMutation, mergeMutation }) {
  const { t } = useTranslation();
  const [isRenameDialogOpen, setIsRenameDialogOpen] = useState(false);
  const [isMergeDialogOpen, setIsMergeDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [newName, setNewName] = useState(tag.name);
  const [mergeTargetId, setMergeTargetId] = useState("");
  const [error, setError] = useState(null);

  const handleArchiveToggle = () => {
    updateMutation.mutate({
      id: tag.id,
      payload: { is_active: !tag.is_active }
    });
  };

  const handleRenameSubmit = (e) => {
    e.preventDefault();
    if (!newName.trim() || newName === tag.name) {
      setIsRenameDialogOpen(false);
      return;
    }
    setError(null);
    updateMutation.mutate(
      {
        id: tag.id,
        payload: { name: newName.trim() }
      },
      {
        onSuccess: () => {
          setIsRenameDialogOpen(false);
        },
        onError: (err) => {
          const detail = err.message || "Failed to rename";
          setError(detail);
        }
      }
    );
  };

  const handleDeleteConfirm = () => {
    setError(null);
    deleteMutation.mutate(tag.id, {
      onSuccess: () => {
        setIsDeleteDialogOpen(false);
      },
      onError: (err) => {
        const detail = err.message || "Failed to delete";
        setError(detail);
      }
    });
  };

  const handleMergeSubmit = (e) => {
    e.preventDefault();
    if (!mergeTargetId) return;
    setError(null);
    mergeMutation.mutate(
      {
        target_id: parseInt(mergeTargetId),
        source_ids: [tag.id]
      },
      {
        onSuccess: () => {
          setIsMergeDialogOpen(false);
        },
        onError: (err) => {
          const detail = err.message || "Failed to merge";
          setError(detail);
        }
      }
    );
  };

  const availableMergeTargets = categoryTags.filter(t => t.id !== tag.id);

  return (
    <>
      <Card className={!tag.is_active ? "opacity-70" : ""}>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <div className="flex items-center gap-2 overflow-hidden pr-2">
            <CardTitle className="text-base font-bold truncate">
              {tag.name}
            </CardTitle>
            {!tag.is_active && (
              <Badge variant="secondary" className="font-normal text-xs whitespace-nowrap">
                {t("common.archived", { defaultValue: "Archived" })}
              </Badge>
            )}
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="h-8 w-8 p-0" disabled={updateMutation.isPending}>
                <span className="sr-only">Open menu</span>
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => {
                setNewName(tag.name);
                setError(null);
                setIsRenameDialogOpen(true);
              }}>
                <Pencil className="mr-2 h-4 w-4" />
                <span>{t("common.rename", { defaultValue: "Rename" })}</span>
              </DropdownMenuItem>
              
              {availableMergeTargets.length > 0 && (
                <DropdownMenuItem onClick={() => {
                  setMergeTargetId("");
                  setError(null);
                  setIsMergeDialogOpen(true);
                }}>
                  <Combine className="mr-2 h-4 w-4" />
                  <span>{t("common.mergeInto", { defaultValue: "Merge Into..." })}</span>
                </DropdownMenuItem>
              )}

              <DropdownMenuSeparator />
              {tag.scorecard.tx_count === 0 ? (
                <DropdownMenuItem 
                  onClick={() => {
                    setError(null);
                    setIsDeleteDialogOpen(true);
                  }}
                  className="text-destructive focus:text-destructive"
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  <span>{t("common.delete", { defaultValue: "Delete" })}</span>
                </DropdownMenuItem>
              ) : (
                <DropdownMenuItem onClick={handleArchiveToggle}>
                  {tag.is_active ? (
                    <>
                      <Archive className="mr-2 h-4 w-4" />
                      <span>{t("common.archive", { defaultValue: "Archive" })}</span>
                    </>
                  ) : (
                    <>
                      <ArchiveRestore className="mr-2 h-4 w-4" />
                      <span>{t("common.restore", { defaultValue: "Restore" })}</span>
                    </>
                  )}
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 mt-2 text-sm">
            <div className="flex flex-col space-y-1">
              <span className="text-muted-foreground text-xs uppercase tracking-wider">
                {t("taxonomy.txCount", { defaultValue: "Transactions" })}
              </span>
              <span className="font-medium">{tag.scorecard.tx_count}</span>
            </div>
            <div className="flex flex-col space-y-1">
              <span className="text-muted-foreground text-xs uppercase tracking-wider">
                {t("taxonomy.lifetimeSpent", { defaultValue: "Lifetime Spent" })}
              </span>
              <span className="font-medium text-destructive">
                {formatUzs(tag.scorecard.lifetime_spent)}
              </span>
            </div>
            <div className="flex flex-col space-y-1">
              <span className="text-muted-foreground text-xs uppercase tracking-wider">
                {t("taxonomy.firstUsed", { defaultValue: "First Used" })}
              </span>
              <span className="font-medium">
                {tag.scorecard.first_used ? new Date(tag.scorecard.first_used).toLocaleDateString() : "-"}
              </span>
            </div>
            <div className="flex flex-col space-y-1">
              <span className="text-muted-foreground text-xs uppercase tracking-wider">
                {t("taxonomy.lastUsed", { defaultValue: "Last Used" })}
              </span>
              <span className="font-medium">
                {tag.scorecard.last_used ? new Date(tag.scorecard.last_used).toLocaleDateString() : "-"}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Dialog open={isRenameDialogOpen} onOpenChange={setIsRenameDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>{t("taxonomy.renameTag", { defaultValue: "Rename Tag" })}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleRenameSubmit}>
            <div className="grid gap-4 py-4">
              <div className="flex flex-col gap-2">
                <Input
                  id="name"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder={tag.name}
                  autoFocus
                />
                {error && (
                  <p className="text-sm text-destructive">{error}</p>
                )}
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setIsRenameDialogOpen(false)}>
                {t("common.cancel", { defaultValue: "Cancel" })}
              </Button>
              <Button type="submit" disabled={updateMutation.isPending || !newName.trim()}>
                {updateMutation.isPending 
                  ? t("common.saving", { defaultValue: "Saving..." }) 
                  : t("common.save", { defaultValue: "Save changes" })}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={isMergeDialogOpen} onOpenChange={setIsMergeDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>{t("taxonomy.mergeTag", { defaultValue: "Merge Subcategory" })}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleMergeSubmit}>
            <div className="grid gap-4 py-4">
              <p className="text-sm text-muted-foreground">
                All transactions associated with <strong>{tag.name}</strong> will be reassigned to the target you select below. <strong>{tag.name}</strong> will then be permanently deleted. This action cannot be undone.
              </p>
              <div className="flex flex-col gap-2">
                <Select value={mergeTargetId} onValueChange={setMergeTargetId}>
                  <SelectTrigger>
                    <SelectValue placeholder={t("taxonomy.selectTarget", { defaultValue: "Select target tag..." })} />
                  </SelectTrigger>
                  <SelectContent>
                    {availableMergeTargets.map(target => (
                      <SelectItem key={target.id} value={target.id.toString()}>
                        {target.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {error && (
                  <p className="text-sm text-destructive">{error}</p>
                )}
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setIsMergeDialogOpen(false)}>
                {t("common.cancel", { defaultValue: "Cancel" })}
              </Button>
              <Button type="submit" disabled={mergeMutation.isPending || !mergeTargetId}>
                {mergeMutation.isPending 
                  ? t("common.merging", { defaultValue: "Merging..." }) 
                  : t("common.confirmMerge", { defaultValue: "Confirm Merge" })}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={isDeleteDialogOpen} onOpenChange={(open) => {
        setIsDeleteDialogOpen(open);
        if (!open) setError(null);
      }}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>{t("taxonomy.deleteTag", { defaultValue: "Delete Subcategory" })}</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-muted-foreground mb-4">
              {t("taxonomy.confirmDelete", { defaultValue: "Are you sure you want to permanently delete this subcategory? This action cannot be undone." })}
            </p>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDeleteDialogOpen(false)}>
              {t("common.cancel", { defaultValue: "Cancel" })}
            </Button>
            <Button variant="destructive" onClick={handleDeleteConfirm} disabled={deleteMutation.isPending}>
              {deleteMutation.isPending 
                ? t("common.deleting", { defaultValue: "Deleting..." }) 
                : t("common.delete", { defaultValue: "Delete" })}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

export function TaxonomyHub() {
  const { t } = useTranslation();
  const taxonomyQuery = useTaxonomyQuery();
  const { createMutation, updateMutation, deleteMutation, mergeMutation } = useTaxonomyMutations();

  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [createCategory, setCreateCategory] = useState("");
  const [createName, setCreateName] = useState("");
  const [createError, setCreateError] = useState(null);

  const handleCreateSubmit = (e) => {
    e.preventDefault();
    if (!createCategory || !createName.trim()) return;
    
    setCreateError(null);
    createMutation.mutate(
      { category: createCategory, name: createName.trim() },
      {
        onSuccess: () => {
          setIsCreateDialogOpen(false);
          setCreateCategory("");
          setCreateName("");
        },
        onError: (err) => {
          setCreateError(err.message || "Failed to create subcategory");
        }
      }
    );
  };

  if (taxonomyQuery.isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-1/3" />
        <Skeleton className="h-[200px] w-full" />
        <Skeleton className="h-[200px] w-full" />
      </div>
    );
  }

  if (taxonomyQuery.isError) {
    return (
      <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-destructive">
        {t("common.errorLoading", { defaultValue: "Failed to load taxonomy data" })}
      </div>
    );
  }

  const tags = taxonomyQuery.data || [];

  // Group tags by category
  const groupedTags = tags.reduce((acc, tag) => {
    if (!acc[tag.category]) {
      acc[tag.category] = [];
    }
    acc[tag.category].push(tag);
    return acc;
  }, {});

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">
            {t("taxonomy.hubTitle", { defaultValue: "Subcategory Taxonomy Hub" })}
          </h2>
          <p className="text-muted-foreground mt-2">
            {t("taxonomy.hubDescription", { 
              defaultValue: "Manage your global subcategories. View lifetime scorecards to understand your historical tracking habits." 
            })}
          </p>
        </div>
        <Button onClick={() => setIsCreateDialogOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          {t("common.add", { defaultValue: "Add Subcategory" })}
        </Button>
      </div>

      {Object.keys(groupedTags).length === 0 ? (
        <div className="text-center py-10 text-muted-foreground">
          {t("taxonomy.noTags", { defaultValue: "No subcategories found. Start budgeting to create tags!" })}
        </div>
      ) : (
        Object.entries(groupedTags).map(([category, categoryTags]) => (
          <div key={category} className="space-y-4">
            <h3 className="text-xl font-semibold border-b pb-2 capitalize">
              {category.replace(/_/g, " ")}
            </h3>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {categoryTags.map((tag) => (
                <TaxonomyTagCard 
                  key={tag.id} 
                  tag={tag} 
                  categoryTags={categoryTags}
                  updateMutation={updateMutation} 
                  deleteMutation={deleteMutation}
                  mergeMutation={mergeMutation}
                />
              ))}
            </div>
          </div>
        ))
      )}

      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>{t("taxonomy.createTag", { defaultValue: "Add Subcategory" })}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreateSubmit}>
            <div className="grid gap-4 py-4">
              <div className="flex flex-col gap-2">
                <Select value={createCategory} onValueChange={setCreateCategory}>
                  <SelectTrigger>
                    <SelectValue placeholder={t("taxonomy.selectCategory", { defaultValue: "Select Category..." })} />
                  </SelectTrigger>
                  <SelectContent>
                    {CATEGORIES.map(category => (
                      <SelectItem key={category} value={category}>
                        {category}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-2">
                <Input
                  id="create-name"
                  value={createName}
                  onChange={(e) => setCreateName(e.target.value)}
                  placeholder={t("taxonomy.newTagName", { defaultValue: "Subcategory name" })}
                  autoFocus
                />
                {createError && (
                  <p className="text-sm text-destructive">{createError}</p>
                )}
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                {t("common.cancel", { defaultValue: "Cancel" })}
              </Button>
              <Button type="submit" disabled={createMutation.isPending || !createCategory || !createName.trim()}>
                {createMutation.isPending 
                  ? t("common.creating", { defaultValue: "Creating..." }) 
                  : t("common.create", { defaultValue: "Create" })}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
