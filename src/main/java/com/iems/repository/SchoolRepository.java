package com.iems.repository;

import java.util.List;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import com.iems.model.entity.School;

@Repository
public interface SchoolRepository extends JpaRepository<School, Long> {
    List<School> findByActiveTrue();
    Page<School> findByActiveTrue(Pageable pageable);
    List<School> findByNameContainingIgnoreCase(String name);
    List<School> findByCityAndActive(String city, Boolean active);
}